"""
Test Case Runner
Executes a single test case in a Chrome window via browser-use + LLM (LiteLLM proxy by default),
reports per-step pass/fail, saves screenshots.
"""
import asyncio
import json
import random
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import settings
from common.utils.logger import logger
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args
from features.functional.core.browser.screenshot_file_store import save_screenshot_b64
from features.functional.core.browser.runner_action_text import action_description_from_output
from features.functional.core.browser.llm_gate import (
    LLMCircuitOpen,
    LLMErrorKind,
    classify_llm_error,
    is_retryable_kind,
)
from features.functional.core.llm_prompts.test_execution import (
    build_auth_section,
    format_steps_for_prompt,
    should_inject_project_credentials,
)
from features.functional.core.llm_prompts.registry import get_prompt
from features.functional.core.status_narrator import narrate_case_result


def _infra_result(
    *,
    steps: List[Dict[str, Any]],
    screenshots: List[str],
    agent_logs: List[Dict[str, Any]],
    duration_ms: int,
    error_kind: str,
    error: str,
    summary: str,
) -> Dict[str, Any]:
    raw = {
        "status": "error",
        "overall": "error",
        "screenshots": list(screenshots),
        "logs": agent_logs,
        "step_results": [],
        "steps_total": len(steps),
        "steps_passed": 0,
        "steps_failed": 0,
        "summary": summary,
        "duration_ms": duration_ms,
        "error": error,
        "infra_error": True,
        "error_kind": error_kind,
    }
    return narrate_case_result(raw, steps)
from features.functional.utils.credentials_redaction import redact_known_credentials

# In-memory store for live polling — keyed by "{run_id}:{test_case_id}"
_tc_progress: Dict[str, Dict[str, Any]] = {}


class TestRunCancelled(Exception):
    """Raised when the user cancels the run while the agent is executing."""


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
            from features.functional.core.accuracy.gates import VerdictGate
            from features.functional.core.accuracy.types import VerdictSource

            return VerdictGate.tag_verdict(
                _normalize_verdict(parsed, total_steps),
                VerdictSource.PARSED,
            )
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
            from features.functional.core.accuracy.gates import VerdictGate
            from features.functional.core.accuracy.types import VerdictSource

            return VerdictGate.tag_verdict(
                _synthesize_verdict_from_history(narrative, total_steps, True),
                VerdictSource.FALLBACK,
            )
        if ok is False:
            logger.info("[TestCaseRunner] Verdict JSON missing; using agent is_successful()=False fallback.")
            from features.functional.core.accuracy.gates import VerdictGate
            from features.functional.core.accuracy.types import VerdictSource

            return VerdictGate.tag_verdict(
                _synthesize_verdict_from_history(narrative, total_steps, False),
                VerdictSource.FALLBACK,
            )

    logger.warning("[TestCaseRunner] No parseable verdict and no agent success flag — inconclusive.")
    from features.functional.core.accuracy.gates import VerdictGate
    from features.functional.core.accuracy.types import VerdictSource

    return VerdictGate.tag_verdict(
        {
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
            "inconclusive": True,
        },
        VerdictSource.INCONCLUSIVE,
    )


# ── LLM ──────────────────────────────────────────────────────────────────────

def _llm(model_override: Optional[str] = None):
    from features.functional.core.browser.browser_use_llm import get_browser_use_llm

    return get_browser_use_llm(model_override=model_override)


def _llms(model_override: Optional[str] = None):
    from features.functional.core.browser.browser_use_llm import get_browser_use_llms

    return get_browser_use_llms(model_override=model_override)


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
        capture_screenshots: bool = True,
        browser_context: Optional[Any] = None,
        on_step_callback: Optional[Any] = None,
        execution_run_id: Optional[int] = None,
        llm_model: Optional[str] = None,
        session_context: Optional[str] = None,
        extra_prompt_hint: Optional[str] = None,
        wallclock_timeout_s: Optional[int] = None,
        reassign_count: int = 0,
    ) -> Dict[str, Any]:
        return await self._run_impl(
            run_id, test_case_id, title, description, preconditions,
            steps, app_url, username, password, use_google_signin, headless,
            capture_screenshots, browser_context, on_step_callback, execution_run_id,
            llm_model=llm_model,
            session_context=session_context,
            extra_prompt_hint=extra_prompt_hint,
            wallclock_timeout_s=wallclock_timeout_s,
            reassign_count=reassign_count,
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
        capture_screenshots: bool,
        browser_context: Optional[Any] = None,
        on_step_callback: Optional[Any] = None,
        execution_run_id: Optional[int] = None,
        llm_model: Optional[str] = None,
        session_context: Optional[str] = None,
        extra_prompt_hint: Optional[str] = None,
        wallclock_timeout_s: Optional[int] = None,
        reassign_count: int = 0,
    ) -> Dict[str, Any]:
        from browser_use import Agent, Browser, BrowserProfile
        from features.functional.services.run_progress_manager import RunProgressManager

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

        progress_mgr = RunProgressManager()
        if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            cleanup_tc_progress(f"{run_id}:{test_case_id}")
            return {
                "status": "cancelled",
                "overall": "cancelled",
                "step_results": [],
                "screenshots": [],
                "logs": [],
                "steps_total": len(steps),
                "steps_passed": 0,
                "steps_failed": 0,
                "summary": "Run cancelled before browser started.",
                "duration_ms": dur,
                "error": None,
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

        async def _on_step(_state: Any, output: Any, step_num: int) -> None:
            if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                raise TestRunCancelled()
            step_counter[0] = step_num
            # Screenshot is captured after actions in _on_step_end (post-action evidence).

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
                "screenshot_path": None,
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

        async def _on_step_end(agent: Any) -> None:
            """Persist viewport screenshot after the step's actions have run."""
            if not capture_screenshots:
                return
            if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                return
            if not agent_logs:
                return
            session = getattr(agent, "browser_session", None)
            if session is None:
                return
            last = agent_logs[-1]
            step_num = last.get("agent_step")
            if step_num is None:
                return
            from features.functional.core.screenshots import should_capture_agent_frame

            if not should_capture_agent_frame(
                current_count=len(screenshots),
                agent_step=int(step_num) if step_num is not None else 0,
            ):
                return
            try:
                summary = await session.get_browser_state_summary(include_screenshot=True)
            except Exception as exc:
                logger.warning(f"[TestCaseRunner] Post-action screenshot failed step={step_num}: {exc}")
                return
            b64 = getattr(summary, "screenshot", None)
            if not b64:
                return
            path = save_screenshot_b64(b64, run_id, test_case_id, step_num)
            if not path:
                return
            last["screenshot_path"] = path
            if path not in screenshots:
                screenshots.append(path)
            pct = min(90, 5 + step_num * (85 // max(len(steps) * 2, 1)))
            set_tc_progress(key, {
                "status": "running",
                "percentage": pct,
                "current_step": last.get("description") or "",
                "screenshots": list(screenshots),
                "logs": list(agent_logs),
            })

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
        prompt_version, prompt_template = get_prompt("test_execution")
        task = prompt_template.format(
            app_url=app_url,
            auth_section=auth_section,
            title=title,
            description=description or "N/A",
            preconditions=preconditions or "None",
            steps_formatted=steps_fmt,
            total_steps=len(steps),
        )
        if session_context == "already_authenticated":
            task += (
                "\n\nSESSION CONTEXT: The browser session is already authenticated "
                "from a prior case in this group. Do NOT re-login or re-navigate to "
                "the login page unless a step explicitly requires it. Skip redundant "
                "setup and continue from the current app state.\n"
            )
        if extra_prompt_hint:
            task += f"\n\n{extra_prompt_hint.strip()}\n"
        try:
            from features.functional.core.browser.llm_gate import get_gate

            health = get_gate().health_hint()
            if health:
                task += f"\n\n{health}\n"
        except Exception:
            pass
        logger.info(
            f"[TestCaseRunner] tc={test_case_id} prompt=test_execution@{prompt_version} "
            f"model={llm_model or (settings.BROWSER_USE_LLM_MODEL or settings.LITELLM_MODEL)}"
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
        
        max_retries = int(getattr(settings, "LLM_RETRY_MAX", 3) or 3)
        retry_base = float(getattr(settings, "LLM_RETRY_BASE_S", 3.0) or 3.0)
        retry_count = 0
        result: Any = None

        # Cap agent steps so a runaway case fails fast. Scale a little with the
        # guide length so long legitimate cases still have headroom.
        _cfg_max_steps = int(getattr(settings, "TEST_CASE_MAX_AGENT_STEPS", 40) or 40)
        max_agent_steps = max(_cfg_max_steps, len(steps) * 3 + 5)
        # Adaptive per-case wall-clock (4m / 10m / 15m). Explicit override wins.
        from features.functional.core.case_budget import budget_for_case

        if wallclock_timeout_s is not None:
            wallclock_timeout_s = int(wallclock_timeout_s)
        else:
            wallclock_timeout_s = int(
                budget_for_case(steps, reassign_count=reassign_count)["wallclock_timeout_s"]
            )
        logger.info(
            "[TestCaseRunner] tc=%s wallclock=%ss steps=%s reassign=%s",
            test_case_id,
            wallclock_timeout_s,
            len(steps),
            reassign_count,
        )

        def _backoff_with_jitter(attempt: int) -> float:
            """Full-jitter backoff so lanes don't retry in lockstep (thundering herd)."""
            ceiling = retry_base * (2 ** attempt)
            return round(random.uniform(0, ceiling), 2)

        async def _run_agent_with_cancel(agent: Any) -> Any:
            """Run browser-use Agent; stop promptly when user cancels (numeric execution_run_id)."""
            if execution_run_id is None:
                return await agent.run(max_steps=max_agent_steps, on_step_end=_on_step_end)

            async def _wait_for_cancel() -> None:
                while not progress_mgr.is_cancel_requested(execution_run_id):
                    await asyncio.sleep(0.25)

            agent_task = asyncio.create_task(agent.run(max_steps=max_agent_steps, on_step_end=_on_step_end))
            poll_task = asyncio.create_task(_wait_for_cancel())
            done, pending = await asyncio.wait(
                [agent_task, poll_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

            if agent_task in done and not agent_task.cancelled():
                poll_task.cancel()
                try:
                    await poll_task
                except asyncio.CancelledError:
                    pass
                exc = agent_task.exception()
                if exc:
                    if isinstance(exc, TestRunCancelled):
                        raise exc
                    raise exc
                return agent_task.result()

            # Cancel was requested before agent finished
            if not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except (asyncio.CancelledError, Exception):
                    pass
            try:
                br = getattr(agent, "browser", None)
                if br is not None:
                    closer = getattr(br, "close", None)
                    if closer:
                        out = closer()
                        if asyncio.iscoroutine(out):
                            await out
            except Exception as be:
                logger.warning(f"[TestCaseRunner] browser close after cancel: {be}")
            raise TestRunCancelled()

        while retry_count < max_retries:
            try:
                if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                    cleanup_tc_progress(key)
                    dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                    return {
                        "status": "cancelled",
                        "overall": "cancelled",
                        "step_results": [],
                        "screenshots": list(screenshots),
                        "logs": agent_logs,
                        "steps_total": len(steps),
                        "steps_passed": 0,
                        "steps_failed": 0,
                        "summary": "Run cancelled before agent start.",
                        "duration_ms": dur,
                        "error": None,
                    }

                primary_llm, fallback_llm = _llms(llm_model)
                agent_kwargs: Dict[str, Any] = {
                    "task": task,
                    "llm": primary_llm,
                    "browser": browser,
                    "browser_profile": BrowserProfile(
                        headless=headless,
                        is_local=True,
                        disable_security=True,
                        args=default_browser_chrome_args(),
                        enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
                    ) if not browser else None,
                    "sensitive_data": sensitive_data,
                    "register_new_step_callback": _on_step,
                    "use_vision": True,
                }
                if fallback_llm is not None:
                    agent_kwargs["fallback_llm"] = fallback_llm
                agent = Agent(**agent_kwargs)

                # Re-check cancellation immediately after agent creation to avoid late browser launch.
                if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                    raise TestRunCancelled()

                if browser:
                    try:
                        await browser.start()
                    except Exception:
                        pass
                    # If cancel arrived while browser was starting, stop before agent.run.
                    if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                        raise TestRunCancelled()

                if wallclock_timeout_s > 0:
                    result = await asyncio.wait_for(
                        _run_agent_with_cancel(agent), timeout=wallclock_timeout_s
                    )
                else:
                    result = await _run_agent_with_cancel(agent)

                # Evaluate the verdict now so an inconclusive outcome (LLM/agent
                # error, NOT a real test failure) can be retried with backoff
                # instead of recording a false failure. Accuracy > speed.
                final_text = ""
                try:
                    if hasattr(result, "final_result"):
                        final_text = str(result.final_result()) or ""
                    elif hasattr(result, "__str__"):
                        final_text = str(result)
                except Exception:
                    pass
                verdict = _parse_verdict(final_text, len(steps), history=result)

                if verdict.get("inconclusive") and retry_count < max_retries - 1:
                    retry_count += 1
                    wait_time = _backoff_with_jitter(retry_count)
                    logger.warning(
                        f"[TestCaseRunner] tc={test_case_id} inconclusive result "
                        f"(likely transient LLM/rate-limit). Retry {retry_count}/{max_retries} "
                        f"in {wait_time}s."
                    )
                    if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                        raise TestRunCancelled()
                    await asyncio.sleep(wait_time)
                    continue

                break
            except TestRunCancelled:
                cleanup_tc_progress(key)
                dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                return {
                    "status": "cancelled",
                    "overall": "cancelled",
                    "step_results": [],
                    "screenshots": list(screenshots),
                    "logs": agent_logs,
                    "steps_total": len(steps),
                    "steps_passed": 0,
                    "steps_failed": 0,
                    "summary": "Run cancelled during execution.",
                    "duration_ms": dur,
                    "error": None,
                }
            except asyncio.TimeoutError:
                # Wall-clock cap hit — treat as retryable transient (hung page/agent).
                retry_count += 1
                if retry_count >= max_retries:
                    dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                    logger.error(
                        f"[TestCaseRunner] tc={test_case_id} exceeded wall-clock "
                        f"{wallclock_timeout_s}s (exhausted retries)"
                    )
                    return _infra_result(
                        steps=steps,
                        screenshots=screenshots,
                        agent_logs=agent_logs,
                        duration_ms=dur,
                        error_kind=LLMErrorKind.TIMEOUT.value,
                        error="wallclock_timeout",
                        summary=f"Case exceeded wall-clock timeout ({wallclock_timeout_s}s).",
                    )
                wait_time = _backoff_with_jitter(retry_count)
                logger.warning(
                    f"⚠ tc={test_case_id} wall-clock timeout (attempt {retry_count}/{max_retries}). "
                    f"Retrying in {wait_time}s."
                )
                await asyncio.sleep(wait_time)
            except Exception as exc:
                kind = classify_llm_error(exc)

                # Unrecoverable infrastructure errors (budget exhausted, circuit
                # open, auth) must NOT be retried and must NOT be recorded as a
                # real test failure. Flag them so the orchestrator can PAUSE the
                # run and resume once the proxy is healthy — this is exactly the
                # run #14 failure mode (214 empty "errors") we're eliminating.
                unrecoverable = (
                    isinstance(exc, LLMCircuitOpen)
                    or kind in (LLMErrorKind.BUDGET, LLMErrorKind.AUTH)
                )
                try:
                    from features.functional.core.browser.llm_gate import get_gate

                    if get_gate().should_pause() and kind == LLMErrorKind.RATE:
                        unrecoverable = True
                except Exception:
                    pass
                if unrecoverable:
                    dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                    logger.error(
                        f"[TestCaseRunner] tc={test_case_id} unrecoverable LLM "
                        f"infra error ({kind.value}) — not a test failure: {str(exc)[:160]}"
                    )
                    return _infra_result(
                        steps=steps,
                        screenshots=screenshots,
                        agent_logs=agent_logs,
                        duration_ms=dur,
                        error_kind=kind.value,
                        error=f"llm_{kind.value}",
                        summary=(
                            f"LLM infrastructure unavailable ({kind.value}). Not a test "
                            "failure — case should be re-run after the proxy recovers."
                        ),
                    )

                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"[TestCaseRunner] run_id={run_id} — agent raised (exhausted retries): {exc!r}")
                    dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                    infra = is_retryable_kind(kind)
                    raw = {
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
                        "infra_error": infra,
                        "error_kind": kind.value,
                    }
                    return narrate_case_result(raw, steps) if infra else raw

                wait_time = _backoff_with_jitter(retry_count)
                logger.info(
                    f"⚠ Agent run failed (attempt {retry_count}/{max_retries}, kind={kind.value}). "
                    f"Retrying in {wait_time}s... Error: {str(exc)[:100]}"
                )
                await asyncio.sleep(wait_time)

        dur = int((datetime.utcnow() - start).total_seconds() * 1000)
        from features.functional.core.accuracy.gates import ScreenshotGate, VerdictGate
        from features.functional.core.accuracy.types import VerdictSource

        step_results = verdict.get("steps", [])
        passed = sum(1 for s in step_results if s.get("status") == "passed")
        failed = len(step_results) - passed
        inconclusive = bool(verdict.get("inconclusive"))
        verdict_source = str(verdict.get("verdict_source") or VerdictSource.PARSED.value)

        if inconclusive:
            # Exhausted retries and still no usable / parsed verdict → ERROR,
            # never a synthetic all-failed test failure (accuracy gate).
            from features.functional.core.screenshots import ScreenshotAgent

            exhausted = VerdictGate.exhausted_payload(
                screenshots=list(screenshots),
                agent_logs=agent_logs,
                steps_total=len(steps),
                duration_ms=dur,
                source=verdict_source,
                original_steps=steps,
            )
            return ScreenshotAgent.apply_to_result(exhausted)

        overall = "passed" if verdict.get("overall") == "passed" else "failed"
        payload: Dict[str, Any] = {
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
            "verdict_source": verdict_source,
        }
        shot_fail = ScreenshotGate.evaluate(
            capture_screenshots=capture_screenshots,
            screenshots=screenshots,
            agent_logs=agent_logs,
            overall=overall,
        )
        if shot_fail:
            payload.update(shot_fail)
        else:
            # Curate evidence set so UI never shows dozens of agent frames.
            from features.functional.core.screenshots import ScreenshotAgent

            ScreenshotAgent.apply_to_result(payload)
        return payload
