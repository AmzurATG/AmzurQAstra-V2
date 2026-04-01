"""
Browser Agent Service
Runs integrity checks in a visible Chrome window using browser-use 0.12+.
Default LLM: LiteLLM proxy (ChatLiteLLM); optional direct Gemini via settings.
"""
import asyncio
import base64
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings
from common.utils.logger import logger

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

# ─── In-memory progress store ─────────────────────────────────────────────────
# Maps run_id → progress dict so GET /status can poll without a DB hit.

_progress_store: Dict[str, Dict[str, Any]] = {}


def get_progress(run_id: str) -> Optional[Dict[str, Any]]:
    return _progress_store.get(run_id)


def set_progress(run_id: str, data: Dict[str, Any]) -> None:
    _progress_store[run_id] = data


def cleanup_progress(run_id: str) -> None:
    _progress_store.pop(run_id, None)


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
                "   • Click \"Sign in with Google\" / \"Continue with Google\" (do not use the app's email+password form).\n"
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

    def _humanize_action_dict(self, d: dict) -> str:
        """Turn browser-use action payload into plain language for non-technical users."""
        if not d:
            return "Working on the page…"
        for key, val in d.items():
            if not isinstance(val, dict):
                continue
            k = key.lower()
            if k in ("click", "click_element"):
                idx = val.get("index")
                return f"Clicked item {idx} on the page" if idx is not None else "Clicked something on the page"
            if k in ("input", "input_text"):
                idx = val.get("index")
                return f"Typed into field {idx}" if idx is not None else "Entered text in a field"
            if k in ("navigate", "go_to_url", "goto"):
                full = val.get("url") or ""
                short = full[:80] + ("…" if len(full) > 80 else "")
                return f"Opened: {short}" if full else "Opened a new page"
            if k in ("scroll", "scroll_down", "scroll_up"):
                return "Scrolled the page"
            if k in ("done", "complete"):
                msg = (val.get("text") or val.get("message") or "").strip()
                if msg:
                    return f"Finished — {msg[:280]}" + ("…" if len(msg) > 280 else "")
                return "Finished the check"
            if k in ("go_back",):
                return "Went back to the previous page"
            if k in ("switch_tab",):
                return "Switched browser tab"
            if k in ("wait", "wait_for"):
                return "Waited for the page to update"
            if k in ("extract", "extract_content"):
                return "Read content from the page"
            if k == "send_keys":
                return "Sent keyboard input"
        return "Worked on the page"

    def _action_description(self, output: Any) -> str:
        """Extract a human-readable description from AgentOutput."""
        try:
            if output and hasattr(output, "action") and output.action:
                parts = []
                for act in output.action:
                    model_dump = act.model_dump(exclude_none=True) if hasattr(act, "model_dump") else {}
                    parts.append(self._humanize_action_dict(model_dump))
                return " · ".join(parts) if parts else "Working…"
        except Exception:
            pass
        return "Working…"

    # ── main entry ────────────────────────────────────────────────────────────

    def _windows_run_sync(
        self,
        run_id: str,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
    ) -> Dict[str, Any]:
        """Run the async agent on a fresh Proactor loop (required for subprocess/Chrome on Windows)."""
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        return asyncio.run(
            self._run_impl(run_id, app_url, username, password, use_google_signin)
        )

    async def run(
        self,
        run_id: str,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
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
            )
        return await self._run_impl(
            run_id, app_url, username, password, use_google_signin
        )

    async def _run_impl(
        self,
        run_id: str,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
    ) -> Dict[str, Any]:
        """Core agent run (must execute on a loop that supports subprocess — e.g. Proactor on Windows)."""
        # Import here to keep startup fast and avoid errors if not yet installed
        from browser_use import Agent, BrowserProfile

        start = datetime.utcnow()
        screenshots: List[str] = []
        steps_data: List[Dict] = []
        step_counter = [0]

        set_progress(run_id, {
            "status": "running",
            "percentage": 5,
            "current_step": "Opening Chrome browser and navigating to the application…",
            "screenshots": [],
            "steps": [],
            "error": None,
        })

        async def _on_step(state: Any, output: Any, step_num: int) -> None:
            step_counter[0] = step_num
            path: Optional[str] = None

            screenshot_b64 = getattr(state, "screenshot", None)
            if screenshot_b64:
                path = self._save_screenshot(screenshot_b64, run_id, step_num)
                if path:
                    screenshots.append(path)

            desc = self._action_description(output)
            steps_data.append({
                "step_number": step_num,
                "description": desc,
                "screenshot_path": path,
            })

            pct = min(90, 5 + step_num * 11)
            set_progress(run_id, {
                "status": "running",
                "percentage": pct,
                "current_step": desc,
                "screenshots": list(screenshots),
                "steps": list(steps_data),
                "error": None,
            })

        sensitive_data = None
        if username and password and not use_google_signin:
            sensitive_data = {"username": username, "password": password}

        try:
            agent = Agent(
                task=self._build_task(app_url, username, password, use_google_signin),
                llm=self._llm(),
                browser_profile=BrowserProfile(
                    headless=False,
                    disable_security=True,
                    enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
                ),
                sensitive_data=sensitive_data,
                register_new_step_callback=_on_step,
                use_vision=True,
            )

            result = await agent.run(max_steps=15)

            # Extract final summary text
            final_text = ""
            try:
                if hasattr(result, "final_result"):
                    final_text = str(result.final_result()) or ""
                elif hasattr(result, "__str__"):
                    final_text = str(result)
            except Exception:
                pass

            _fail_kw = ["fail", "error", "unable", "could not", "not found", "404", "500", "invalid"]
            success = False
            if hasattr(result, "is_successful"):
                flag = result.is_successful()
                if flag is True:
                    success = True
                elif flag is False:
                    success = False
                else:
                    success = not any(kw in final_text.lower() for kw in _fail_kw)
            else:
                success = not any(kw in final_text.lower() for kw in _fail_kw)
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            n = step_counter[0]

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
                "summary": final_text[:500],
                "duration_ms": dur,
                "error": None,
            }
            set_progress(run_id, outcome)
            return outcome

        except Exception as exc:
            logger.error(f"[BrowserAgent] run_id={run_id} — agent raised: {exc!r}")
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            n = step_counter[0]
            err: Dict[str, Any] = {
                "status": "error",
                "overall_status": "error",
                "percentage": 100,
                "current_step": "An error occurred",
                "screenshots": list(screenshots),
                "steps": list(steps_data),
                "steps_total": n,
                "steps_passed": 0,
                "steps_failed": n,
                "summary": str(exc)[:500],
                "duration_ms": dur,
                "error": str(exc),
            }
            set_progress(run_id, err)
            return err
