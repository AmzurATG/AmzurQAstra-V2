"""
Shared Session Runner — executes a group's MERGED STEP SCRIPT inside ONE browser.

Flow:
  1. Open one browser for the entire group.
  2. Build a merged task prompt from the group's deduplicated step list.
  3. Run the browser-use Agent on the merged script.
  4. Capture screenshots keyed to merged_step_number (not per-case step number).
  5. Return raw group result: agent_logs + merged_step_results + screenshots.

The EvaluatorAgent (called by the orchestrator after this returns) fans the
merged results back to each original test case's step_results.

Isolated cases (session_type="isolated") are handled by TestCaseRunner — unchanged.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import json
import re

from common.utils.logger import logger
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args
from features.functional.core.browser.screenshot_file_store import save_screenshot_b64
from features.functional.core.browser.runner_action_text import action_description_from_output
from features.functional.core.browser.test_case_runner import TestRunCancelled, set_tc_progress, cleanup_tc_progress
from features.functional.core.execution.execution_plan import ExecutionGroup, MergedStep
from features.functional.core.llm_prompts.merged_execution import build_merged_task_prompt
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.utils.credentials_redaction import (
    redact_known_credentials,
    redact_agent_logs_list,
)
from config import settings


def _error_group_result(reason: str, merged_step_count: int, dur: int = 0) -> Dict[str, Any]:
    return {
        "overall": "error",
        "merged_step_results": [
            {"merged_step_number": i + 1, "status": "error", "actual_result": reason, "adaptation": None}
            for i in range(merged_step_count)
        ],
        "screenshots": [],
        "agent_logs": [],
        "summary": reason,
        "duration_ms": dur,
        "error": reason,
    }


def _cancelled_group_result(merged_step_count: int, dur: int = 0) -> Dict[str, Any]:
    return {
        "overall": "cancelled",
        "merged_step_results": [
            {"merged_step_number": i + 1, "status": "skipped", "actual_result": "Run cancelled.", "adaptation": None}
            for i in range(merged_step_count)
        ],
        "screenshots": [],
        "agent_logs": [],
        "summary": "Run cancelled.",
        "duration_ms": dur,
        "error": None,
    }


def _extract_merged_verdict(text: str, total_merged_steps: int) -> Dict[str, Any]:
    """Parse VERDICT_JSON_START...VERDICT_JSON_END from agent output."""
    if not text:
        return _synthetic_verdict(total_merged_steps, "passed")

    # Try markers first
    match = re.search(
        r"VERDICT_JSON_START\s*(\{.*?\})\s*VERDICT_JSON_END",
        text,
        re.DOTALL,
    )
    if match:
        try:
            data = json.loads(match.group(1))
            return _normalize_merged_verdict(data, total_merged_steps)
        except (json.JSONDecodeError, Exception):
            pass

    # Try fenced JSON
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            return _normalize_merged_verdict(data, total_merged_steps)
        except Exception:
            pass

    # Fallback: determine overall from agent output text
    overall = "failed" if any(w in text.lower() for w in ("failed", "error", "could not")) else "passed"
    return _synthetic_verdict(total_merged_steps, overall)


def _normalize_merged_verdict(data: Dict[str, Any], total: int) -> Dict[str, Any]:
    raw_steps = {
        int(s["merged_step_number"]): s
        for s in data.get("merged_step_results", [])
        if s.get("merged_step_number") is not None
    }
    steps_out = []
    for i in range(1, total + 1):
        s = raw_steps.get(i, {})
        status = str(s.get("status", "skipped")).lower()
        if status not in ("passed", "failed", "skipped", "error"):
            status = "skipped"
        steps_out.append({
            "merged_step_number": i,
            "status": status,
            "actual_result": s.get("actual_result", ""),
            "adaptation": s.get("adaptation"),
            "screenshot_path": None,  # filled in after by _on_step_end
        })
    overall_raw = str(data.get("overall", "")).lower()
    overall = "passed" if overall_raw == "passed" else "failed"
    any_fail = any(s["status"] not in ("passed",) for s in steps_out)
    if any_fail and overall == "passed":
        overall = "failed"
    return {
        "merged_step_results": steps_out,
        "overall": overall,
        "summary": str(data.get("summary", "")),
    }


def _synthetic_verdict(total: int, overall: str) -> Dict[str, Any]:
    return {
        "merged_step_results": [
            {"merged_step_number": i + 1, "status": overall, "actual_result": "", "adaptation": None, "screenshot_path": None}
            for i in range(total)
        ],
        "overall": overall,
        "summary": f"Synthetic verdict ({overall}) — agent did not emit structured JSON.",
    }


class SharedSessionRunner:
    """
    Runs a group's merged step script inside one browser instance.

    Returns raw group result dict. The orchestrator calls EvaluatorAgent
    afterward to fan results back to individual TestResult rows.
    """

    async def run_group(
        self,
        *,
        group: ExecutionGroup,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        headless: bool,
        run_uuid: str,
        execution_run_id: int,
        on_case_step: Optional[Callable] = None,
        on_case_complete: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute the group's merged_steps in one browser.

        Returns a dict with:
          overall, merged_step_results, agent_logs, screenshots, summary, duration_ms, error
        """
        from browser_use import Agent, Browser, BrowserProfile

        progress_mgr = RunProgressManager()
        merged_steps: List[MergedStep] = group.merged_steps
        total_merged = len(merged_steps)

        if not merged_steps:
            return _error_group_result("Group has no merged steps.", 0)

        # ── Open browser once for the whole group ────────────────────────────
        browser = Browser(
            config=BrowserProfile(
                headless=headless,
                is_local=True,
                disable_security=True,
                args=default_browser_chrome_args(),
                enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
            )
        )
        try:
            await browser.start()
        except Exception as exc:
            logger.error(f"[SharedSessionRunner] Browser start failed group={group.group_id}: {exc}")
            return _error_group_result(f"Browser launch failed: {exc}", total_merged)

        start = datetime.utcnow()
        key = f"{run_uuid}:{group.group_id}"
        screenshots: List[str] = []
        agent_logs: List[Dict[str, Any]] = []
        step_counter = [0]

        # ── Build merged task prompt ──────────────────────────────────────────
        task, sensitive_data = build_merged_task_prompt(
            group_label=group.label,
            merged_steps=merged_steps,
            total_cases=len(group.ordered_cases),
            app_url=app_url,
            username=username,
            password=password,
            use_google_signin=use_google_signin,
        )

        set_tc_progress(key, {
            "status": "running",
            "percentage": 5,
            "current_step": f"Starting group: {group.label}",
            "screenshots": [],
            "logs": [],
        })

        async def _on_step(_state: Any, output: Any, step_num: int) -> None:
            if progress_mgr.is_cancel_requested(execution_run_id):
                raise TestRunCancelled()
            step_counter[0] = step_num
            desc = action_description_from_output(output)
            safe_desc = redact_known_credentials(desc or "", username=username, password=password) or (desc or "")
            agent_logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent_step": step_num,
                "description": safe_desc,
                "adaptation": None,
                "screenshot_path": None,
            })
            pct = min(90, 5 + step_num * (85 // max(total_merged * 2, 1)))
            set_tc_progress(key, {
                "status": "running",
                "percentage": pct,
                "current_step": safe_desc,
                "screenshots": list(screenshots),
                "logs": list(agent_logs),
            })
            if on_case_step:
                try:
                    cb = on_case_step(step_num, safe_desc, agent_logs[-1])
                    if asyncio.iscoroutine(cb):
                        await cb
                except Exception:
                    pass

        async def _on_step_end(agent: Any) -> None:
            """Capture a viewport screenshot after each agent step and tag agent_log entry."""
            if progress_mgr.is_cancel_requested(execution_run_id):
                return
            if not agent_logs:
                return
            session = getattr(agent, "browser_session", None)
            if not session:
                return
            last = agent_logs[-1]
            agent_step = last.get("agent_step")
            if agent_step is None:
                return
            try:
                summary = await session.get_browser_state_summary(include_screenshot=True)
                b64 = getattr(summary, "screenshot", None)
                if b64:
                    # Tag screenshot with group_id + agent step (merged step scope)
                    path = save_screenshot_b64(b64, f"{run_uuid}_{group.group_id}", 0, agent_step)
                    if path:
                        last["screenshot_path"] = path
                        if path not in screenshots:
                            screenshots.append(path)
            except Exception as exc:
                logger.warning(f"[SharedSessionRunner] Screenshot failed step={agent_step}: {exc}")

        try:
            from features.functional.core.browser.browser_use_llm import get_browser_use_llm

            agent = Agent(
                task=task,
                llm=get_browser_use_llm(),
                browser=browser,
                sensitive_data=sensitive_data,
                register_new_step_callback=_on_step,
                use_vision=True,
            )

            if progress_mgr.is_cancel_requested(execution_run_id):
                raise TestRunCancelled()

            async def _run_with_cancel() -> Any:
                agent_task = asyncio.create_task(
                    agent.run(max_steps=max(80, total_merged * 6), on_step_end=_on_step_end)
                )
                while not agent_task.done():
                    if progress_mgr.is_cancel_requested(execution_run_id):
                        agent_task.cancel()
                        await asyncio.gather(agent_task, return_exceptions=True)
                        raise TestRunCancelled()
                    await asyncio.sleep(0.3)
                return await agent_task

            result = await _run_with_cancel()

        except TestRunCancelled:
            cleanup_tc_progress(key)
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            await self._close_browser(browser)
            return _cancelled_group_result(total_merged, dur)
        except Exception as exc:
            cleanup_tc_progress(key)
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            logger.error(f"[SharedSessionRunner] group={group.group_id} agent error: {exc}")
            await self._close_browser(browser)
            return _error_group_result(str(exc)[:500], total_merged, dur)
        finally:
            await self._close_browser(browser)

        # ── Parse merged verdict ──────────────────────────────────────────────
        final_text = ""
        try:
            if hasattr(result, "final_result"):
                final_text = str(result.final_result()) or ""
            elif hasattr(result, "__str__"):
                final_text = str(result)
        except Exception:
            pass

        verdict = _extract_merged_verdict(final_text, total_merged)
        dur = int((datetime.utcnow() - start).total_seconds() * 1000)

        # Attach screenshots from agent_logs to the closest merged_step_result by agent_step index
        self._attach_screenshots_to_merged_steps(verdict["merged_step_results"], agent_logs)

        safe_logs = redact_agent_logs_list(agent_logs, username, password)
        cleanup_tc_progress(key)

        overall = verdict["overall"]
        passed = sum(1 for s in verdict["merged_step_results"] if s.get("status") == "passed")

        return {
            "overall": overall,
            "merged_step_results": verdict["merged_step_results"],
            "agent_logs": safe_logs,
            "screenshots": list(screenshots),
            "summary": verdict.get("summary", ""),
            "duration_ms": dur,
            "steps_passed": passed,
            "steps_failed": total_merged - passed,
            "error": None,
        }

    def _attach_screenshots_to_merged_steps(
        self,
        merged_step_results: List[Dict[str, Any]],
        agent_logs: List[Dict[str, Any]],
    ) -> None:
        """
        Map agent_log screenshots to the nearest merged_step_result.

        The agent runs N agent steps for M merged steps (N >= M).
        We divide agent steps evenly across merged steps and assign the last
        screenshot in each agent-step block to that merged step.
        """
        if not agent_logs or not merged_step_results:
            return

        logs_with_shots = [l for l in agent_logs if l.get("screenshot_path")]
        if not logs_with_shots:
            return

        total_merged = len(merged_step_results)
        total_agent = len(logs_with_shots)

        for idx, ms_result in enumerate(merged_step_results):
            # Proportional slice of agent logs for this merged step
            start_i = int(idx * total_agent / total_merged)
            end_i = int((idx + 1) * total_agent / total_merged)
            slice_logs = logs_with_shots[start_i:end_i]
            if slice_logs:
                # Take the last screenshot in the slice (post-action evidence)
                ms_result["screenshot_path"] = slice_logs[-1]["screenshot_path"]

    async def _close_browser(self, browser: Any) -> None:
        try:
            closer = getattr(browser, "close", None)
            if closer:
                out = closer()
                if asyncio.iscoroutine(out):
                    await out
        except Exception as be:
            logger.warning(f"[SharedSessionRunner] Browser close error: {be}")
