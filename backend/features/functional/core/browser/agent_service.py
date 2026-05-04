"""
Browser Agent Service
Runs integrity checks in a visible Chrome window using browser-use 0.12+.
Default LLM: LiteLLM proxy (ChatLiteLLM); optional direct Gemini via settings.
"""
import asyncio
import base64
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from config import settings
from common.utils.logger import logger
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args
from features.functional.utils.credentials_redaction import redact_known_credentials

# ─── Task prompt ─────────────────────────────────────────────────────────────

_TASK_TEMPLATE = """You are a QA testing agent. Verify that a web application is working correctly.

Target URL: {app_url}

Steps to perform:
1. Navigate to the URL — take note of the landing/login page.
{login_instructions}
3. After landing on the main/dashboard page, confirm it loaded successfully.
4. End your run with a clear PASS or FAIL verdict and the reason.

RULES:
{auth_rules}
- Be concise — maximum 15 steps total.
"""

IC_MAX_STEPS = 15
# BIC UI shows at most this many screenshot-based tiers (matches typical 4–5 captures per run).
IC_UI_MAX_SCREENSHOTS = 5

# Keywords suggesting the app or page is not usable (connection, chrome error pages, etc.)
_FAIL_SUBSTRINGS = (
    "fail",
    "error",
    "unable",
    "could not",
    "not found",
    "404",
    "500",
    "invalid",
    "refused",
    "unreachable",
    "can't be reached",
    "cannot be reached",
    "couldn’t be reached",  # unicode apostrophe variants sometimes appear in UI copy
    "couldn't be reached",
    "timed out",
    "timeout",
    "connection refused",
    "connection reset",
    "err_connection",
    "name not resolved",
    "dns",
    "no internet",
    "network change",
    "offline",
    "ssl error",
    "certificate error",
    "access denied",
    "forbidden",
    "403",
    "502",
    "503",
    "504",
    "network error",
    "this site can't",
    "this page isn",
    "refused to connect",
    "unexpectedly closed",
)

LiveProgressWriter = Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]]

# ─── In-memory progress store ─────────────────────────────────────────────────
# Maps run_id → progress dict so GET /status can poll without a DB hit.

_progress_store: Dict[str, Dict[str, Any]] = {}


def get_progress(run_id: str) -> Optional[Dict[str, Any]]:
    return _progress_store.get(run_id)


def set_progress(run_id: str, data: Dict[str, Any]) -> None:
    _progress_store[run_id] = data


def cleanup_progress(run_id: str) -> None:
    _progress_store.pop(run_id, None)


def _redact_ic_text(
    text: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> str:
    """Strip known credentials from integrity-check text shown in Summary / errors."""
    if not text:
        return ""
    out = redact_known_credentials(text, username=username, password=password)
    return out if out is not None else ""


class _IcUiProgress:
    """
    Integrity-check progress for the UI: login-flow milestones + ≤5 screenshot tiers + step fallback.
    Caller enforces monotonic increase across emits. Caps at 99 until terminal outcome (100%).
    """

    def __init__(self, *, manual_login: bool, google_sso: bool) -> None:
        self.manual_login = manual_login
        self.google_sso = google_sso
        self.nav_count = 0
        self.input_count = 0
        self.click_count = 0
        self.done_count = 0

    def observe_kinds(self, kinds: List[str]) -> None:
        for k in kinds:
            if k == "navigate":
                self.nav_count += 1
            elif k == "input":
                self.input_count += 1
            elif k == "click":
                self.click_count += 1
            elif k == "done":
                self.done_count += 1

    def _screenshot_pct(self, screenshot_count: int) -> int:
        n = max(0, min(int(screenshot_count), IC_UI_MAX_SCREENSHOTS))
        tiers = {0: 0, 1: 18, 2: 36, 3: 54, 4: 72, 5: 88}
        return tiers.get(n, 88)

    def _step_fallback_pct(self, step_num: int) -> int:
        """Sparse milestones but many agent steps (e.g. repeated waits)."""
        s = max(0, min(int(step_num), IC_MAX_STEPS))
        return min(88, 8 + int((s / float(IC_MAX_STEPS)) * 80))

    def _milestone_pct(self) -> int:
        if self.google_sso:
            p = 10
            if self.nav_count >= 1:
                p = max(p, 14)
            if self.click_count >= 1:
                p = max(p, 32)
            if self.click_count >= 2:
                p = max(p, 52)
            if self.click_count >= 3:
                p = max(p, 72)
            if self.click_count >= 4:
                p = max(p, 85)
            if self.input_count >= 1:
                p = max(p, 48)
            if self.done_count >= 1:
                p = max(p, 99)
            return min(99, p)

        if self.manual_login:
            p = 10
            if self.nav_count >= 1:
                p = max(p, 14)
            # Cookie / dismiss banners: small bump, does not skip to "logged in".
            if self.click_count >= 1 and self.input_count == 0:
                p = max(p, 22)
            if self.input_count >= 1:
                p = max(p, 25)
            if self.input_count >= 2:
                p = max(p, 50)
            # Login submit after both fields (spec: ~80%). Single-field logins may only reach 72 until done.
            if self.input_count >= 2 and self.click_count >= 1:
                p = max(p, 80)
            elif self.input_count >= 1 and self.click_count >= 1:
                p = max(p, 72)
            if self.done_count >= 1:
                p = max(p, 99)
            return min(99, p)

        # No credentials — verify page only; rely more on screenshots + light interactions.
        p = 10
        if self.nav_count >= 1:
            p = max(p, 14)
        if self.input_count >= 1:
            p = max(p, 30)
        if self.input_count >= 2:
            p = max(p, 48)
        if self.click_count >= 1:
            p = max(p, 55)
        if self.click_count >= 2:
            p = max(p, 72)
        if self.done_count >= 1:
            p = max(p, 99)
        return min(99, p)

    def running_pct(self, screenshot_count: int, step_num: int) -> int:
        return min(
            99,
            max(
                self._milestone_pct(),
                self._screenshot_pct(screenshot_count),
                self._step_fallback_pct(step_num),
            ),
        )


def _final_text_indicates_failure(final_text: str) -> bool:
    low = final_text.lower()
    if any(k in low for k in _FAIL_SUBSTRINGS):
        return True
    if re.search(r"\bfail(ed|ure|ing)?\b", low):
        return True
    return False


# ─── Service ──────────────────────────────────────────────────────────────────


class BrowserAgentService:
    """Executes an integrity check in a visible Chrome window via browser-use 0.12+."""

    def __init__(self) -> None:
        self._screenshots_dir = Path(settings.SCREENSHOTS_DIR)
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _llm(self):
        from features.functional.core.browser.browser_use_llm import get_browser_use_llm

        return get_browser_use_llm()

    def _build_task(
        self,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
    ) -> str:
        if use_google_signin:
            login = (
                "2. This app uses Google Sign-In only for this run:\n"
                '   • Click "Sign in with Google" / "Continue with Google" (do not use the app\'s email+password form).\n'
                "   • Complete Google's account picker and consent in the browser window.\n"
                f"   • Preferred account email when asked: {username or '(choose the correct work account)'}\n"
                "   • If MFA appears, the user may need to complete it in this browser window.\n"
                "   • Do not type app passwords or placeholders into Google or app fields unless you are on Google's own password step."
            )
            auth_rules = (
                "- Use only the Google Sign-In flow for this run — not the app's local email/password form.\n"
                "- Do not invent passwords or use words like 'PlaceholderPassword'."
            )
        elif username and password:
            login = (
                "2. Log in with the manual email + password form:\n"
                f"   • Email address: {username}\n"
                "   • When the agent uses the input action for the email field, use text exactly: <secret>username</secret>\n"
                "   • For the password field, use text exactly: <secret>password</secret> (system injects the real password; preserve every character including capitals).\n"
                "   • Do not type sample text, 'PlaceholderPassword', or guessed passwords.\n"
                "   • Click Sign In / Login after both fields are filled.\n"
                "   • If both Google and manual login exist, prefer manual email/password for this run."
            )
            auth_rules = (
                "- Prefer the manual login form over Google SSO when both are available.\n"
                "- Never invent credentials; only use the <secret>…</secret> placeholders for typing."
            )
        else:
            login = "2. No credentials provided — just verify the page loads without errors."
            auth_rules = (
                "- If a login is required but no credentials were given, report what you see and FAIL with a clear reason.\n"
                "- If only SSO exists, note that credentials were not provided for SSO."
            )
        return _TASK_TEMPLATE.format(
            app_url=app_url,
            login_instructions=login,
            auth_rules=auth_rules,
        )

    def _save_screenshot(self, b64: str, run_id: str, step: int) -> Optional[str]:
        try:
            ts = datetime.utcnow().strftime("%H%M%S%f")
            fname = f"ic_{run_id[:8]}_s{step:02d}_{ts}.png"
            (self._screenshots_dir / fname).write_bytes(base64.b64decode(b64))
            return f"/screenshots/{fname}"
        except Exception as exc:
            logger.warning(f"[BrowserAgent] Screenshot save failed step {step}: {exc}")
            return None

    def _action_kinds_from_output(self, output: Any) -> List[str]:
        kinds: List[str] = []
        try:
            if output and hasattr(output, "action") and output.action:
                for act in output.action:
                    model_dump = (
                        act.model_dump(exclude_none=True) if hasattr(act, "model_dump") else {}
                    )
                    for key, val in model_dump.items():
                        if not isinstance(val, dict):
                            continue
                        k = key.lower()
                        if k in ("click", "click_element"):
                            kinds.append("click")
                        elif k in ("input", "input_text"):
                            kinds.append("input")
                        elif k in ("navigate", "go_to_url", "goto"):
                            kinds.append("navigate")
                        elif k in ("scroll", "scroll_down", "scroll_up"):
                            kinds.append("scroll")
                        elif k in ("done", "complete"):
                            kinds.append("done")
                        elif k in ("wait", "wait_for"):
                            kinds.append("wait")
                        elif k in ("extract", "extract_content"):
                            kinds.append("extract")
                        elif k in ("go_back",):
                            kinds.append("back")
                        elif k in ("switch_tab",):
                            kinds.append("tab")
                        elif k == "send_keys":
                            kinds.append("keys")
        except Exception:
            pass
        return kinds

    def _friendly_step_headline(self, output: Any, has_login_creds: bool) -> str:
        """Short, non-technical line for the integrity-check progress UI."""
        kinds = self._action_kinds_from_output(output)
        if not kinds:
            return "Working on the page…"
        if kinds == ["done"] or (len(kinds) == 1 and kinds[0] == "done"):
            return "Finishing the check"
        inputs = sum(1 for k in kinds if k == "input")
        clicks = sum(1 for k in kinds if k == "click")
        navs = sum(1 for k in kinds if k == "navigate")
        if navs and inputs == 0 and clicks == 0:
            return "Opening the application"
        if inputs >= 2 and clicks >= 1:
            if has_login_creds:
                return "Entered username and password, then continued"
            return "Filled in multiple fields and continued"
        if inputs >= 2:
            return "Filled in the form fields"
        if inputs >= 1 and clicks >= 1:
            return "Entered details and clicked to continue"
        if inputs == 1:
            return "Filled in a form field"
        if clicks >= 1:
            return "Clicked to continue on the page"
        if any(k == "scroll" for k in kinds):
            return "Scrolled the page"
        if any(k == "wait" for k in kinds):
            return "Waiting for the page to update"
        if any(k == "extract" for k in kinds):
            return "Read content from the page"
        return "Working on the page…"

    async def _emit_progress(
        self,
        run_id: str,
        payload: Dict[str, Any],
        live_progress_writer: LiveProgressWriter,
    ) -> None:
        set_progress(run_id, payload)
        if live_progress_writer:
            try:
                await live_progress_writer(run_id, payload)
            except Exception as exc:
                logger.warning(f"[BrowserAgent] live_progress DB write failed run_id={run_id}: {exc}")

    # ── main entry ────────────────────────────────────────────────────────────

    def _windows_run_sync(
        self,
        run_id: str,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        live_progress_writer: LiveProgressWriter,
    ) -> Dict[str, Any]:
        """Run the async agent on a fresh Proactor loop (required for subprocess/Chrome on Windows)."""
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        return asyncio.run(
            self._run_impl(
                run_id,
                app_url,
                username,
                password,
                use_google_signin,
                live_progress_writer,
            )
        )

    async def run(
        self,
        run_id: str,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
        live_progress_writer: LiveProgressWriter = None,
    ) -> Dict[str, Any]:
        """
        Execute the integrity check task.
        Updates _progress_store at every step for live polling.
        Returns the final result dict.
        """
        if sys.platform == "win32":
            return await asyncio.to_thread(
                self._windows_run_sync,
                run_id,
                app_url,
                username,
                password,
                use_google_signin,
                live_progress_writer,
            )
        return await self._run_impl(
            run_id,
            app_url,
            username,
            password,
            use_google_signin,
            live_progress_writer,
        )

    async def _run_impl(
        self,
        run_id: str,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
        live_progress_writer: LiveProgressWriter = None,
    ) -> Dict[str, Any]:
        """Core agent run (must execute on a loop that supports subprocess — e.g. Proactor on Windows)."""
        # Import here to keep startup fast and avoid errors if not yet installed
        from browser_use import Agent, BrowserProfile

        start = datetime.utcnow()
        screenshots: List[str] = []
        steps_data: List[Dict] = []
        step_counter = [0]
        has_login_creds = bool(username and password) and not use_google_signin
        ic_prog = _IcUiProgress(manual_login=has_login_creds, google_sso=use_google_signin)
        last_emit_pct = [12]

        def _emit_running_pct(*, step_num: int) -> int:
            raw = ic_prog.running_pct(len(screenshots), step_num)
            v = max(last_emit_pct[0], raw)
            last_emit_pct[0] = v
            return v

        await self._emit_progress(
            run_id,
            {
                "status": "running",
                "percentage": last_emit_pct[0],
                "current_step": "Opening Chrome browser and navigating to the application…",
                "screenshots": [],
                "steps": [],
                "error": None,
            },
            live_progress_writer,
        )

        async def _on_step(_state: Any, output: Any, step_num: int) -> None:
            step_counter[0] = step_num
            # Post-action screenshot is saved in _on_step_end.

            kinds = self._action_kinds_from_output(output)
            ic_prog.observe_kinds(kinds)

            desc = self._friendly_step_headline(output, has_login_creds)
            steps_data.append(
                {
                    "step_number": step_num,
                    "description": desc,
                    "screenshot_path": None,
                }
            )

            pct = _emit_running_pct(step_num=step_num)
            await self._emit_progress(
                run_id,
                {
                    "status": "running",
                    "percentage": pct,
                    "current_step": desc,
                    "screenshots": list(screenshots),
                    "steps": list(steps_data),
                    "error": None,
                },
                live_progress_writer,
            )

        async def _on_step_end(agent: Any) -> None:
            if not steps_data:
                return
            session = getattr(agent, "browser_session", None)
            if session is None:
                return
            last = steps_data[-1]
            step_num = last.get("step_number")
            if step_num is None:
                return
            try:
                summary = await session.get_browser_state_summary(include_screenshot=True)
            except Exception as exc:
                logger.warning(f"[BrowserAgent] Post-action screenshot failed step={step_num}: {exc}")
                return
            b64 = getattr(summary, "screenshot", None)
            if not b64:
                return
            path = self._save_screenshot(b64, run_id, step_num)
            if not path:
                return
            last["screenshot_path"] = path
            if path not in screenshots:
                screenshots.append(path)
            pct = _emit_running_pct(step_num=step_num)
            await self._emit_progress(
                run_id,
                {
                    "status": "running",
                    "percentage": pct,
                    "current_step": last.get("description") or "",
                    "screenshots": list(screenshots),
                    "steps": list(steps_data),
                    "error": None,
                },
                live_progress_writer,
            )

        sensitive_data = None
        if username and password and not use_google_signin:
            sensitive_data = {"username": username, "password": password}

        try:
            agent = Agent(
                task=self._build_task(app_url, username, password, use_google_signin),
                llm=self._llm(),
                browser_profile=BrowserProfile(
                    headless=False,
                    is_local=True,
                    disable_security=True,
                    args=default_browser_chrome_args(),
                    enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
                ),
                sensitive_data=sensitive_data,
                register_new_step_callback=_on_step,
                use_vision=True,
            )

            result = await agent.run(max_steps=IC_MAX_STEPS, on_step_end=_on_step_end)

            # Extract final summary text
            final_text = ""
            try:
                if hasattr(result, "final_result"):
                    final_text = str(result.final_result()) or ""
                elif hasattr(result, "__str__"):
                    final_text = str(result)
            except Exception:
                pass

            text_fail = _final_text_indicates_failure(final_text)
            success = False
            if hasattr(result, "is_successful"):
                flag = result.is_successful()
                if flag is False:
                    success = False
                elif flag is True:
                    # Do not trust is_successful alone when the narrative describes failure or error pages.
                    success = not text_fail
                else:
                    success = not text_fail
            else:
                success = not text_fail

            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            n = step_counter[0]

            pre_complete_pct = max(last_emit_pct[0], 99)
            last_emit_pct[0] = pre_complete_pct
            await self._emit_progress(
                run_id,
                {
                    "status": "running",
                    "percentage": pre_complete_pct,
                    "current_step": "Wrapping up result…",
                    "screenshots": list(screenshots),
                    "steps": list(steps_data),
                    "error": None,
                },
                live_progress_writer,
            )

            summary_safe = _redact_ic_text(final_text[:500], username, password)
            outcome: Dict[str, Any] = {
                "status": "completed",
                "overall_status": "passed" if success else "failed",
                "percentage": 100,
                "current_step": "Completed",
                "screenshots": list(screenshots),
                "steps": list(steps_data),
                "steps_total": n,
                "steps_passed": n if success else max(0, n - 1),
                "steps_failed": 0 if success else 1,
                "summary": summary_safe,
                "duration_ms": dur,
                "error": None,
            }
            await self._emit_progress(run_id, outcome, live_progress_writer)
            return outcome

        except Exception as exc:
            logger.error(f"[BrowserAgent] run_id={run_id} — agent raised: {exc!r}")
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            n = step_counter[0]
            exc_s = str(exc)
            run_pct = max(last_emit_pct[0], min(92, ic_prog.running_pct(len(screenshots), n)))
            last_emit_pct[0] = run_pct
            err: Dict[str, Any] = {
                "status": "error",
                "overall_status": "error",
                "percentage": max(5, min(92, run_pct)),
                "current_step": "An error occurred",
                "screenshots": list(screenshots),
                "steps": list(steps_data),
                "steps_total": n,
                "steps_passed": 0,
                "steps_failed": n,
                "summary": _redact_ic_text(exc_s[:500], username, password),
                "duration_ms": dur,
                "error": _redact_ic_text(exc_s, username, password),
            }
            await self._emit_progress(run_id, err, live_progress_writer)
            return err
