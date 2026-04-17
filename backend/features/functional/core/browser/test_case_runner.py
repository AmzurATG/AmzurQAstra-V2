"""
Test Case Runner
Executes a single test case in a Chrome window via browser-use + LLM (LiteLLM proxy by default),
reports per-step pass/fail, saves screenshots.
"""
import asyncio
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from common.utils.logger import logger
from features.functional.core.browser.screenshot_file_store import save_screenshot_b64
from features.functional.core.browser.runner_action_text import action_description_from_output
from features.functional.core.llm_prompts.test_execution import (
    TEST_EXECUTION_PROMPT,
    build_auth_section,
    format_steps_for_prompt,
    should_inject_project_credentials,
)
from features.functional.utils.credentials_redaction import redact_known_credentials

# In-memory store for live polling — keyed by "{run_id}:{test_case_id}"
_tc_progress: Dict[str, Dict[str, Any]] = {}


def get_tc_progress(key: str) -> Optional[Dict[str, Any]]:
    return _tc_progress.get(key)


def set_tc_progress(key: str, data: Dict[str, Any]) -> None:
    _tc_progress[key] = data


def cleanup_tc_progress(key: str) -> None:
    _tc_progress.pop(key, None)


# ── helpers ──────────────────────────────────────────────────────────────────

def _extract_balanced_json_object(text: str, start: int) -> Optional[str]:
    """Slice from `start` (index of '{') through the matching '}', respecting JSON strings."""
    if start < 0 or start >= len(text) or text[start] != "{":
        return None
    depth = 0
    i = start
    in_string = False
    escape = False
    while i < len(text):
        c = text[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        i += 1
    return None


def _try_json_loads(blob: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(blob)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_verdict_from_markers(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON between VERDICT_JSON_START and VERDICT_JSON_END using brace matching."""
    if not text:
        return None
    start_marker = "VERDICT_JSON_START"
    pos = text.find(start_marker)
    if pos == -1:
        return None
    brace_at = text.find("{", pos + len(start_marker))
    if brace_at == -1:
        return None
    blob = _extract_balanced_json_object(text, brace_at)
    if not blob:
        return None
    verdict = _try_json_loads(blob)
    if verdict and isinstance(verdict.get("steps"), list):
        return verdict
    return None


def _parse_verdict_fenced_json(text: str) -> Optional[Dict[str, Any]]:
    """Accept ```json ... ``` blocks."""
    if not text:
        return None
    for m in re.finditer(r"```(?:json)?\s*(\{)", text, re.IGNORECASE | re.DOTALL):
        blob = _extract_balanced_json_object(text, m.start(1))
        if not blob:
            continue
        verdict = _try_json_loads(blob)
        if verdict and isinstance(verdict.get("steps"), list) and "overall" in verdict:
            return verdict
    return None


def _parse_verdict_scan_objects(text: str) -> Optional[Dict[str, Any]]:
    """Scan for any top-level JSON object that looks like a verdict."""
    if not text or '"steps"' not in text:
        return None
    best: Optional[Dict[str, Any]] = None
    best_len = 0
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        blob = _extract_balanced_json_object(text, i)
        if not blob or len(blob) < 20:
            continue
        verdict = _try_json_loads(blob)
        if not verdict or not isinstance(verdict.get("steps"), list):
            continue
        if "overall" not in verdict:
            continue
        if len(blob) > best_len:
            best = verdict
            best_len = len(blob)
    return best


def _normalize_step_status(raw: Any) -> str:
    s = str(raw or "").lower().strip()
    if s in ("pass", "passed", "success", "ok", "true"):
        return "passed"
    if s in ("fail", "failed", "failure", "false"):
        return "failed"
    if s in ("skip", "skipped"):
        return "skipped"
    return "error"


def _normalize_overall(raw: Any) -> str:
    s = str(raw or "").lower().strip()
    if s in ("pass", "passed", "success", "ok", "true"):
        return "passed"
    if s in ("fail", "failed", "failure", "false", "error"):
        return "failed"
    return "failed"


def _normalize_verdict(verdict: Dict[str, Any], total_steps: int) -> Dict[str, Any]:
    """Ensure step count matches guide, normalize statuses, derive overall if missing."""
    raw_steps = verdict.get("steps") or []
    steps_out: List[Dict[str, Any]] = []
    for i in range(total_steps):
        if i < len(raw_steps) and isinstance(raw_steps[i], dict):
            rs = raw_steps[i]
            sn = rs.get("step_number", i + 1)
            try:
                sn = int(sn)
            except (TypeError, ValueError):
                sn = i + 1
            steps_out.append({
                "step_number": sn,
                "status": _normalize_step_status(rs.get("status")),
                "actual_result": str(rs.get("actual_result") or rs.get("actual") or ""),
                "adaptation": rs.get("adaptation"),
            })
        else:
            steps_out.append({
                "step_number": i + 1,
                "status": "error",
                "actual_result": "Agent did not report this step in the verdict JSON.",
                "adaptation": None,
            })

    # Re-number sequentially if needed
    for i, s in enumerate(steps_out):
        s["step_number"] = i + 1

    overall_raw = verdict.get("overall")
    if overall_raw is None or str(overall_raw).strip() == "":
        all_passed = all(_normalize_step_status(s.get("status")) == "passed" for s in steps_out)
        overall_norm = "passed" if all_passed else "failed"
    else:
        overall_norm = _normalize_overall(overall_raw)

    any_bad = any(_normalize_step_status(s.get("status")) != "passed" for s in steps_out)
    if any_bad and overall_norm == "passed":
        overall_norm = "failed"

    summary = verdict.get("summary") or verdict.get("message") or ""
    if not isinstance(summary, str):
        summary = str(summary)

    return {
        "steps": steps_out,
        "overall": overall_norm,
        "summary": summary,
    }


def _synthesize_verdict_from_history(
    narrative: str,
    total_steps: int,
    agent_success: bool,
) -> Dict[str, Any]:
    """When the model omits VERDICT_JSON but browser-use recorded done(success=…)."""
    status = "passed" if agent_success else "failed"
    narrative = (narrative or "").strip()
    clip = narrative[:1200] + ("…" if len(narrative) > 1200 else "")
    steps: List[Dict[str, Any]] = []
    for i in range(total_steps):
        steps.append({
            "step_number": i + 1,
            "status": status,
            "actual_result": clip if i == total_steps - 1 else "Assessed from agent completion (no separate per-step JSON).",
            "adaptation": None,
        })
    return {
        "steps": steps,
        "overall": "passed" if agent_success else "failed",
        "summary": narrative[:2000] if narrative else (
            "Completed per agent success flag; verdict JSON was missing." if agent_success
            else "Failed per agent success flag; verdict JSON was missing."
        ),
    }


def _parse_verdict(
    text: str,
    total_steps: int,
    history: Any = None,
) -> Dict[str, Any]:
    """Extract verdict JSON from agent output; fall back to history.is_successful() when JSON is missing."""
    parsed: Optional[Dict[str, Any]] = None
    for extractor in (
        _parse_verdict_from_markers,
        _parse_verdict_fenced_json,
        _parse_verdict_scan_objects,
    ):
        parsed = extractor(text or "")
        if parsed:
            break

    if parsed:
        try:
            return _normalize_verdict(parsed, total_steps)
        except Exception as exc:
            logger.warning(f"[TestCaseRunner] Verdict normalization failed: {exc}")

    # No parseable JSON — use browser-use completion signal (all mission types, incl. negative / literal)
    narrative = (text or "").strip()
    if history is not None and callable(getattr(history, "is_successful", None)):
        try:
            ok = history.is_successful()
        except Exception:
            ok = None
        if ok is True:
            logger.info("[TestCaseRunner] Verdict JSON missing; using agent is_successful()=True fallback.")
            return _synthesize_verdict_from_history(narrative, total_steps, True)
        if ok is False:
            logger.info("[TestCaseRunner] Verdict JSON missing; using agent is_successful()=False fallback.")
            return _synthesize_verdict_from_history(narrative, total_steps, False)

    logger.warning("[TestCaseRunner] No parseable verdict and no agent success flag — marking error.")
    return {
        "steps": [
            {
                "step_number": i + 1,
                "status": "error",
                "actual_result": "Could not parse agent output",
                "adaptation": None,
            }
            for i in range(total_steps)
        ],
        "overall": "failed",
        "summary": "Agent did not return parseable VERDICT_JSON and task completion status was unavailable.",
    }


# ── LLM ──────────────────────────────────────────────────────────────────────

def _llm():
    from features.functional.core.browser.browser_use_llm import get_browser_use_llm

    return get_browser_use_llm()


# ── Runner ───────────────────────────────────────────────────────────────────

class TestCaseRunner:
    """Runs a single test case against a live application."""

    async def run(
        self,
        run_id: str,
        test_case_id: int,
        title: str,
        description: str,
        preconditions: str,
        steps: List[Dict[str, Any]],
        app_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_google_signin: bool = False,
        headless: bool = False,
        browser_context: Optional[Any] = None,
        on_step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        return await self._run_impl(
            run_id, test_case_id, title, description, preconditions,
            steps, app_url, username, password, use_google_signin, headless,
            browser_context, on_step_callback,
        )

    async def _run_impl(
        self,
        run_id: str,
        test_case_id: int,
        title: str,
        description: str,
        preconditions: str,
        steps: List[Dict[str, Any]],
        app_url: Optional[str],
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        headless: bool,
        browser_context: Optional[Any] = None,
        on_step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        from browser_use import Agent, Browser, BrowserProfile

        start = datetime.utcnow()
        app_url = (app_url or "").strip()
        if not app_url:
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            logger.error("[TestCaseRunner] Missing app_url — cannot run browser automation")
            return {
                "status": "error",
                "overall": "failed",
                "step_results": [],
                "screenshots": [],
                "logs": [],
                "steps_total": len(steps),
                "steps_passed": 0,
                "steps_failed": len(steps),
                "summary": "No application URL configured for this run.",
                "duration_ms": dur,
                "error": "missing_app_url",
            }
        if not steps:
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            return {
                "status": "error",
                "overall": "failed",
                "step_results": [],
                "screenshots": [],
                "logs": [],
                "steps_total": 0,
                "steps_passed": 0,
                "steps_failed": 0,
                "summary": "Test case has no steps to execute.",
                "duration_ms": dur,
                "error": "no_steps",
            }

        key = f"{run_id}:{test_case_id}"
        screenshots: List[str] = []
        agent_logs: List[Dict[str, Any]] = []
        step_counter = [0]

        set_tc_progress(key, {
            "status": "running", "percentage": 5,
            "current_step": "Launching browser…",
            "screenshots": [], "logs": [],
        })

        async def _on_step(state: Any, output: Any, step_num: int) -> None:
            step_counter[0] = step_num
            path: Optional[str] = None
            ss_b64 = getattr(state, "screenshot", None)
            if ss_b64:
                path = save_screenshot_b64(ss_b64, run_id, test_case_id, step_num)
                if path:
                    screenshots.append(path)

            desc = action_description_from_output(output)
            safe_desc = desc
            if isinstance(desc, str):
                safe_desc = redact_known_credentials(
                    desc, username=username, password=password
                ) or desc
            logger.info(f"[TestCaseRunner] Step {step_num} Action: {safe_desc}")

            adaptation = None
            if hasattr(output, "adaptation") and output.adaptation:
                raw_ad = output.adaptation
                if isinstance(raw_ad, str):
                    adaptation = redact_known_credentials(
                        raw_ad, username=username, password=password
                    ) or raw_ad
                else:
                    adaptation = raw_ad
                logger.info(f"[TestCaseRunner] AI ADAPTATION: {adaptation}")

            agent_logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent_step": step_num,
                "description": safe_desc,
                "adaptation": adaptation,
                "screenshot_path": path,
            })
            pct = min(90, 5 + step_num * (85 // max(len(steps) * 2, 1)))
            set_tc_progress(key, {
                "status": "running", "percentage": pct,
                "current_step": safe_desc,
                "screenshots": list(screenshots),
                "logs": list(agent_logs),
            })
            if on_step_callback:
                try:
                    if asyncio.iscoroutinefunction(on_step_callback):
                        await on_step_callback(step_num, desc, agent_logs[-1] if agent_logs else None)
                    else:
                        on_step_callback(step_num, desc, agent_logs[-1] if agent_logs else None)
                except Exception as cb_err:
                    logger.warning(f"[TestCaseRunner] Progress callback failed: {cb_err}")

        inject_creds = should_inject_project_credentials(
            title, description or "", preconditions or "", steps
        )
        logger.info(
            f"[TestCaseRunner] tc={test_case_id} inject_project_secrets={inject_creds}"
        )

        auth_section = build_auth_section(
            username,
            password,
            use_google_signin,
            inject_project_secrets=inject_creds,
        )
        steps_fmt = format_steps_for_prompt([
            {"step_number": i + 1, **s} if "step_number" not in s else s
            for i, s in enumerate(steps)
        ], app_url=app_url)
        task = TEST_EXECUTION_PROMPT.format(
            app_url=app_url,
            auth_section=auth_section,
            title=title,
            description=description or "N/A",
            preconditions=preconditions or "None",
            steps_formatted=steps_fmt,
            total_steps=len(steps),
        )

        sensitive_data = None
        if (
            inject_creds
            and username
            and password
            and not use_google_signin
        ):
            sensitive_data = {"username": username, "password": password}

        browser = None
        if browser_context:
            browser = browser_context
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                agent = Agent(
                    task=task,
                    llm=_llm(),
                    browser=browser,
                    browser_profile=BrowserProfile(
                        headless=headless,
                        is_local=True,
                        disable_security=True,
                        args=[
                            "--disable-save-password-bubble", 
                            "--disable-autofill", 
                            "--disable-notifications",
                            "--disable-infobars",
                            "--no-default-browser-check",
                            "--no-first-run",
                        ],
                        enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
                    ) if not browser else None,
                    sensitive_data=sensitive_data,
                    register_new_step_callback=_on_step,
                    use_vision=True,  # Explicitly enable vision prowess
                )
                
                # Ensure browser is started (idempotent)
                if browser:
                    try:
                        await browser.start()
                    except:
                        pass
                        
                result = await agent.run(max_steps=80)
                break # Success, exit retry loop
            except Exception as exc:
                retry_count += 1
                if retry_count >= max_retries:
                    raise exc
                
                wait_time = 2 ** retry_count
                logger.info(f"⚠ Browser startup failed (attempt {retry_count}/{max_retries}). Retrying in {wait_time}s... Error: {str(exc)[:100]}")
                await asyncio.sleep(wait_time)

        try:
            # result is already set from agent.run above
            final_text = ""
            try:
                if hasattr(result, "final_result"):
                    final_text = str(result.final_result()) or ""
                elif hasattr(result, "__str__"):
                    final_text = str(result)
            except Exception:
                pass

            verdict = _parse_verdict(final_text, len(steps), history=result)
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)

            step_results = verdict.get("steps", [])
            passed = sum(1 for s in step_results if s.get("status") == "passed")
            failed = len(step_results) - passed
            overall = "passed" if verdict.get("overall") == "passed" else "failed"

            outcome: Dict[str, Any] = {
                "status": "completed",
                "overall": overall,
                "step_results": step_results,
                "screenshots": list(screenshots),
                "logs": agent_logs,
                "steps_total": len(steps),
                "steps_passed": passed,
                "steps_failed": failed,
                "summary": verdict.get("summary", ""),
                "duration_ms": dur,
                "error": None,
            }
            return outcome

        except Exception as exc:
            logger.error(f"[TestCaseRunner] run_id={run_id} — agent raised: {exc!r}")
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            err: Dict[str, Any] = {
                "status": "error",
                "overall": "error",
                "percentage": 100,
                "current_step": "An error occurred",
                "screenshots": list(screenshots),
                "logs": agent_logs,
                "steps_total": len(steps),
                "steps_passed": 0,
                "steps_failed": len(steps),
                "summary": str(exc)[:500],
                "duration_ms": dur,
                "error": str(exc),
            }
            return err
