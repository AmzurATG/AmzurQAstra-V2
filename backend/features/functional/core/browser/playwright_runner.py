"""
Playwright Fast Runner
======================
Executes a single test case using raw Playwright (no AI / LLM) for maximum speed.

Each structured action step (navigate, click, fill, select, assert_text, etc.) is
mapped directly to a Playwright API call.  Steps with action="custom" fall back to
a best-effort natural-language heuristic:
  - If the description mentions a URL or starts with "go to / navigate / open" →
    treated as navigate.
  - Otherwise the step is marked as "skipped (requires AI)" so the result shows up
    clearly without blocking the rest of the test.

Why use this runner?
  - Zero LLM calls  → no token cost, no latency
  - Local Chromium  → no Steel session overhead
  - ~1-5 s per step vs ~30-60 s for the browser-use AI path
  - Useful for regression suites with deterministic, selector-driven steps

Execution strategy name:  "playwright"
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from common.utils.logger import logger
from features.functional.core.browser.screenshot_file_store import save_screenshot_b64
from features.functional.services.run_progress_manager import RunProgressManager

# In-memory live progress (reuses same store as TestCaseRunner)
from features.functional.core.browser.test_case_runner import (
    set_tc_progress,
    cleanup_tc_progress,
    TestRunCancelled,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _is_navigate_custom(description: str) -> Optional[str]:
    """If a custom step looks like a navigation action, return the URL (or None)."""
    desc = (description or "").strip().lower()
    for prefix in ("go to ", "navigate to ", "open ", "visit ", "browse to "):
        if desc.startswith(prefix):
            url_part = description.strip()[len(prefix):].strip().strip("\"'")
            if url_part.startswith("http") or "." in url_part:
                return url_part
    url_match = re.search(r"https?://\S+", description or "")
    if url_match:
        return url_match.group()
    return None


def _step_passed(step_number: int, desc: str, actual: str) -> Dict[str, Any]:
    return {
        "step_number": step_number,
        "status": "passed",
        "description": desc,
        "actual_result": actual,
        "adaptation": None,
        "screenshot_path": None,
    }


def _step_failed(step_number: int, desc: str, error: str) -> Dict[str, Any]:
    return {
        "step_number": step_number,
        "status": "failed",
        "description": desc,
        "actual_result": error,
        "adaptation": None,
        "screenshot_path": None,
    }


def _step_skipped(step_number: int, desc: str, reason: str) -> Dict[str, Any]:
    return {
        "step_number": step_number,
        "status": "skipped",
        "description": desc,
        "actual_result": reason,
        "adaptation": None,
        "screenshot_path": None,
    }


# ── Runner ────────────────────────────────────────────────────────────────────


class PlaywrightRunner:
    """Executes a single test case with raw Playwright — no AI required."""

    # Default timeout per action in milliseconds
    ACTION_TIMEOUT = 10_000

    async def run(
        self,
        *,
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
        headless: bool = True,
        execution_run_id: Optional[int] = None,
        on_step_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Run a test case with Playwright.

        Returns the same shape dict as TestCaseRunner.run() so the service layer
        doesn't need any special-casing.
        """
        start = datetime.utcnow()
        app_url = (app_url or "").strip()
        if not app_url:
            return self._error(steps, "No application URL configured.", 0)
        if not steps:
            return self._error([], "Test case has no steps.", 0)

        key = f"{run_id}:{test_case_id}"
        screenshots: List[str] = []
        step_results: List[Dict[str, Any]] = []
        agent_logs: List[Dict[str, Any]] = []
        progress_mgr = RunProgressManager()

        set_tc_progress(key, {
            "status": "running", "percentage": 5,
            "current_step": "Launching browser (Playwright)…",
            "screenshots": [], "logs": [],
        })

        from playwright.async_api import async_playwright, TimeoutError as PwTimeout

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                ignore_https_errors=True,
            )
            page = await context.new_page()

            try:
                # Navigate to app_url as the first implicit step
                try:
                    await page.goto(app_url, timeout=20_000, wait_until="domcontentloaded")
                except Exception as nav_err:
                    logger.warning(f"[PlaywrightRunner] Initial goto failed: {nav_err}")

                total = len(steps)
                for idx, step in enumerate(steps):
                    if execution_run_id is not None and progress_mgr.is_cancel_requested(execution_run_id):
                        raise TestRunCancelled()

                    step_num = step.get("step_number", idx + 1)
                    action = (step.get("action") or "custom").lower()
                    target = step.get("target") or ""
                    value = step.get("value") or ""
                    desc = step.get("description") or f"Step {step_num}: {action} {target}"

                    pct = int(10 + (idx / total) * 85)
                    set_tc_progress(key, {
                        "status": "running", "percentage": pct,
                        "current_step": desc[:120],
                        "screenshots": list(screenshots),
                        "logs": list(agent_logs),
                    })

                    log_entry: Dict[str, Any] = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "agent_step": step_num,
                        "description": desc,
                        "adaptation": None,
                        "screenshot_path": None,
                    }
                    agent_logs.append(log_entry)

                    if on_step_callback:
                        try:
                            cb = on_step_callback(step_num, desc, log_entry)
                            if asyncio.iscoroutine(cb):
                                await cb
                        except Exception:
                            pass

                    result_dict = await self._execute_step(
                        page=page,
                        step_num=step_num,
                        action=action,
                        target=target,
                        value=value,
                        desc=desc,
                        app_url=app_url,
                    )
                    step_results.append(result_dict)

                    # Screenshot after each step
                    try:
                        b64 = await page.screenshot(type="png", full_page=False)
                        import base64
                        b64_str = base64.b64encode(b64).decode()
                        path = save_screenshot_b64(b64_str, run_id, test_case_id, step_num)
                        if path:
                            result_dict["screenshot_path"] = path
                            log_entry["screenshot_path"] = path
                            screenshots.append(path)
                    except Exception as ss_err:
                        logger.debug(f"[PlaywrightRunner] Screenshot failed step={step_num}: {ss_err}")

                    set_tc_progress(key, {
                        "status": "running", "percentage": pct,
                        "current_step": desc[:120],
                        "screenshots": list(screenshots),
                        "logs": list(agent_logs),
                    })

            except TestRunCancelled:
                cleanup_tc_progress(key)
                dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                return {
                    "status": "cancelled", "overall": "cancelled",
                    "step_results": step_results, "screenshots": screenshots,
                    "logs": agent_logs, "steps_total": total,
                    "steps_passed": 0, "steps_failed": 0,
                    "summary": "Run cancelled.", "duration_ms": dur, "error": None,
                }
            except Exception as exc:
                logger.error(f"[PlaywrightRunner] Fatal error tc={test_case_id}: {exc}")
                cleanup_tc_progress(key)
                dur = int((datetime.utcnow() - start).total_seconds() * 1000)
                return self._error(steps, str(exc)[:400], dur)
            finally:
                try:
                    await context.close()
                    await browser.close()
                except Exception:
                    pass

        cleanup_tc_progress(key)
        dur = int((datetime.utcnow() - start).total_seconds() * 1000)

        passed = sum(1 for s in step_results if s.get("status") == "passed")
        skipped = sum(1 for s in step_results if s.get("status") == "skipped")
        failed = len(step_results) - passed - skipped
        overall = "passed" if failed == 0 and passed > 0 else "failed"

        return {
            "status": "completed",
            "overall": overall,
            "step_results": step_results,
            "screenshots": screenshots,
            "logs": agent_logs,
            "steps_total": len(steps),
            "steps_passed": passed,
            "steps_failed": failed,
            "summary": f"{passed} passed, {failed} failed, {skipped} skipped",
            "duration_ms": dur,
            "error": None,
        }

    # ── Step dispatcher ───────────────────────────────────────────────────────

    async def _execute_step(
        self,
        *,
        page: Any,
        step_num: int,
        action: str,
        target: str,
        value: str,
        desc: str,
        app_url: str,
    ) -> Dict[str, Any]:
        """Map action → Playwright call; return a step result dict."""
        from playwright.async_api import TimeoutError as PwTimeout

        try:
            if action == "navigate":
                url = target or app_url
                if not url.startswith("http"):
                    url = app_url.rstrip("/") + "/" + url.lstrip("/")
                await page.goto(url, timeout=20_000, wait_until="domcontentloaded")
                return _step_passed(step_num, desc, f"Navigated to {url}")

            elif action in ("click",):
                if not target:
                    return _step_failed(step_num, desc, "No target selector provided")
                await page.click(target, timeout=self.ACTION_TIMEOUT)
                return _step_passed(step_num, desc, f"Clicked '{target}'")

            elif action in ("fill", "type"):
                if not target:
                    return _step_failed(step_num, desc, "No target selector provided")
                await page.fill(target, value, timeout=self.ACTION_TIMEOUT)
                return _step_passed(step_num, desc, f"Filled '{target}' with value")

            elif action == "select":
                if not target:
                    return _step_failed(step_num, desc, "No target selector provided")
                await page.select_option(target, value, timeout=self.ACTION_TIMEOUT)
                return _step_passed(step_num, desc, f"Selected '{value}' in '{target}'")

            elif action == "check":
                if not target:
                    return _step_failed(step_num, desc, "No target selector provided")
                await page.check(target, timeout=self.ACTION_TIMEOUT)
                return _step_passed(step_num, desc, f"Checked '{target}'")

            elif action == "uncheck":
                if not target:
                    return _step_failed(step_num, desc, "No target selector provided")
                await page.uncheck(target, timeout=self.ACTION_TIMEOUT)
                return _step_passed(step_num, desc, f"Unchecked '{target}'")

            elif action == "hover":
                if not target:
                    return _step_failed(step_num, desc, "No target selector provided")
                await page.hover(target, timeout=self.ACTION_TIMEOUT)
                return _step_passed(step_num, desc, f"Hovered '{target}'")

            elif action == "wait":
                ms = int(float(value) * 1000) if value else 1000
                if target:
                    await page.wait_for_selector(target, timeout=max(ms, 5_000))
                else:
                    await page.wait_for_timeout(ms)
                return _step_passed(step_num, desc, f"Waited {ms}ms")

            elif action == "screenshot":
                return _step_passed(step_num, desc, "Screenshot captured")

            elif action == "assert_text":
                if not value:
                    return _step_failed(step_num, desc, "No expected text provided for assert_text")
                try:
                    if target:
                        await page.wait_for_selector(
                            f"{target}:has-text(\"{value}\")", timeout=self.ACTION_TIMEOUT
                        )
                    else:
                        await page.wait_for_function(
                            f"document.body.innerText.includes({value!r})", timeout=self.ACTION_TIMEOUT
                        )
                    return _step_passed(step_num, desc, f"Text '{value}' is present")
                except PwTimeout:
                    actual = await page.inner_text("body") if not target else await page.inner_text(target) if await page.is_visible(target) else "element not visible"
                    return _step_failed(step_num, desc, f"Expected text '{value}' not found. Page text: {actual[:200]}")

            elif action == "assert_visible":
                if not target:
                    return _step_failed(step_num, desc, "No target selector for assert_visible")
                is_visible = await page.is_visible(target)
                if is_visible:
                    return _step_passed(step_num, desc, f"Element '{target}' is visible")
                return _step_failed(step_num, desc, f"Element '{target}' is not visible")

            elif action == "assert_url":
                current = page.url
                expected = (value or target or "").strip()
                if expected in current:
                    return _step_passed(step_num, desc, f"URL contains '{expected}' (current: {current})")
                return _step_failed(step_num, desc, f"URL mismatch: expected '{expected}', got '{current}'")

            elif action == "assert_title":
                title_actual = await page.title()
                expected = (value or target or "").strip()
                if expected.lower() in title_actual.lower():
                    return _step_passed(step_num, desc, f"Title '{title_actual}' matches '{expected}'")
                return _step_failed(step_num, desc, f"Title mismatch: expected '{expected}', got '{title_actual}'")

            elif action == "custom":
                # Heuristic: detect navigation by keywords
                nav_url = _is_navigate_custom(desc)
                if nav_url:
                    if not nav_url.startswith("http"):
                        nav_url = app_url.rstrip("/") + "/" + nav_url.lstrip("/")
                    await page.goto(nav_url, timeout=20_000, wait_until="domcontentloaded")
                    return _step_passed(step_num, desc, f"Navigated to {nav_url}")
                # Can't automate this deterministically
                return _step_skipped(
                    step_num, desc,
                    "Custom step requires AI execution — use 'sequential' strategy to run with browser-use"
                )

            else:
                return _step_skipped(step_num, desc, f"Unknown action type: '{action}'")

        except Exception as exc:
            return _step_failed(step_num, desc, str(exc)[:300])

    # ── Error builder ─────────────────────────────────────────────────────────

    @staticmethod
    def _error(steps: List[Dict], msg: str, dur: int) -> Dict[str, Any]:
        return {
            "status": "error", "overall": "error",
            "step_results": [], "screenshots": [],
            "logs": [], "steps_total": len(steps),
            "steps_passed": 0, "steps_failed": len(steps),
            "summary": msg, "duration_ms": dur, "error": msg,
        }
