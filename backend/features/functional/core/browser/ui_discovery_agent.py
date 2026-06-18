"""
UI Discovery Agent — browser-use exploration that emits structured page inventory.
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from config import settings
from common.utils.logger import logger
from features.functional.core.browser.browser_profile_factory import make_browser_profile
from features.functional.core.llm_prompts.ui_discovery import UI_DISCOVERY_TASK_TEMPLATE
from features.functional.schemas.ui_discovery import UiInventory

UID_MAX_STEPS = 50
LiveProgressWriter = Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]]

_discovery_progress: Dict[str, Dict[str, Any]] = {}


def get_discovery_progress(run_id: str) -> Optional[Dict[str, Any]]:
    return _discovery_progress.get(run_id)


def set_discovery_progress(run_id: str, payload: Dict[str, Any]) -> None:
    _discovery_progress[run_id] = payload


def clear_discovery_progress(run_id: str) -> None:
    _discovery_progress.pop(run_id, None)


def _parse_inventory_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON between INVENTORY_JSON_START and INVENTORY_JSON_END."""
    if not text:
        return None
    start_marker = "INVENTORY_JSON_START"
    end_marker = "INVENTORY_JSON_END"
    start = text.find(start_marker)
    if start == -1:
        return None
    start += len(start_marker)
    end = text.find(end_marker, start)
    if end == -1:
        snippet = text[start:].strip()
    else:
        snippet = text[start:end].strip()
    brace = snippet.find("{")
    if brace == -1:
        return None
    snippet = snippet[brace:]
    depth = 0
    for i, ch in enumerate(snippet):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(snippet[: i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class UiDiscoveryAgent:
    """Explores a web app and returns structured UI inventory."""

    def __init__(self) -> None:
        self._screenshots_dir = Path(settings.SCREENSHOTS_DIR)
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)

    def _llm(self):
        from features.functional.core.browser.browser_use_llm import get_browser_use_llm

        return get_browser_use_llm()

    def _save_screenshot(self, b64: str, run_id: str, step: int) -> Optional[str]:
        try:
            ts = datetime.utcnow().strftime("%H%M%S%f")
            fname = f"uid_{run_id[:8]}_s{step:02d}_{ts}.png"
            (self._screenshots_dir / fname).write_bytes(base64.b64decode(b64))
            return f"/screenshots/{fname}"
        except Exception as exc:
            logger.warning("[UiDiscovery] Screenshot save failed step %s: %s", step, exc)
            return None

    def _build_task(
        self,
        app_url: str,
        actor_role: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
    ) -> str:
        if use_google_signin:
            login = (
                "2. Log in via Google Sign-In:\n"
                '   • Click "Sign in with Google" / "Continue with Google".\n'
                f"   • Preferred account: {username or '(choose work account)'}\n"
            )
            auth_rules = "- Use Google Sign-In flow for this run.\n- Do not invent credentials."
        elif username and password:
            login = (
                "2. Log in with email + password:\n"
                f"   • Email: {username}\n"
                "   • For email field use: <secret>username</secret>\n"
                "   • For password field use: <secret>password</secret>\n"
                "   • Click Sign In / Login after both fields are filled.\n"
            )
            auth_rules = (
                "- Prefer manual login over Google SSO when both exist.\n"
                "- Never invent credentials; use <secret> placeholders only."
            )
        else:
            login = "2. No credentials — explore whatever public pages are accessible."
            auth_rules = "- If login is required without credentials, record the login page only and stop."

        return UI_DISCOVERY_TASK_TEMPLATE.format(
            app_url=app_url,
            actor_role=actor_role,
            login_instructions=login,
            auth_rules=auth_rules,
            max_steps=UID_MAX_STEPS,
        )

    async def _emit_progress(
        self,
        run_id: str,
        payload: Dict[str, Any],
        live_progress_writer: LiveProgressWriter,
    ) -> None:
        set_discovery_progress(run_id, payload)
        if live_progress_writer:
            try:
                await live_progress_writer(run_id, payload)
            except Exception as exc:
                logger.warning("[UiDiscovery] live_progress write failed run_id=%s: %s", run_id, exc)

    def _windows_run_sync(
        self,
        run_id: str,
        app_url: str,
        actor_role: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        live_progress_writer: LiveProgressWriter,
    ) -> Dict[str, Any]:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        return asyncio.run(
            self._run_impl(
                run_id, app_url, actor_role, username, password, use_google_signin, live_progress_writer
            )
        )

    async def run(
        self,
        run_id: str,
        app_url: str,
        actor_role: str = "end_user",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_google_signin: bool = False,
        live_progress_writer: LiveProgressWriter = None,
    ) -> Dict[str, Any]:
        if sys.platform == "win32":
            return await asyncio.to_thread(
                self._windows_run_sync,
                run_id,
                app_url,
                actor_role,
                username,
                password,
                use_google_signin,
                live_progress_writer,
            )
        return await self._run_impl(
            run_id, app_url, actor_role, username, password, use_google_signin, live_progress_writer
        )

    async def _run_impl(
        self,
        run_id: str,
        app_url: str,
        actor_role: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        live_progress_writer: LiveProgressWriter,
    ) -> Dict[str, Any]:
        from browser_use import Agent

        start = datetime.utcnow()
        task = self._build_task(app_url, actor_role, username, password, use_google_signin)
        screenshots: List[str] = []
        step_counter = [0]

        sensitive_data = None
        if username and password and not use_google_signin:
            sensitive_data = {"username": username, "password": password}

        await self._emit_progress(
            run_id,
            {
                "status": "running",
                "percentage": 5,
                "current_step": "Opening Chrome browser…",
                "screenshots": [],
            },
            live_progress_writer,
        )

        async def _on_step(_state: Any, output: Any, step_num: int) -> None:
            step_counter[0] = step_num
            pct = min(90, int(5 + (step_num / UID_MAX_STEPS) * 85))
            await self._emit_progress(
                run_id,
                {
                    "status": "running",
                    "percentage": pct,
                    "current_step": f"Exploring page (step {step_num})…",
                    "screenshots": list(screenshots),
                },
                live_progress_writer,
            )

        async def _on_step_end(agent: Any) -> None:
            session = getattr(agent, "browser_session", None)
            if session is None:
                return
            step_num = step_counter[0]
            try:
                summary = await session.get_browser_state_summary(include_screenshot=True)
            except Exception as exc:
                logger.warning("[UiDiscovery] Post-action screenshot failed step=%s: %s", step_num, exc)
                return
            b64 = getattr(summary, "screenshot", None)
            if not b64:
                return
            path = self._save_screenshot(b64, run_id, step_num)
            if path and path not in screenshots:
                screenshots.append(path)
            pct = min(90, int(5 + (step_num / UID_MAX_STEPS) * 85))
            await self._emit_progress(
                run_id,
                {
                    "status": "running",
                    "percentage": pct,
                    "current_step": f"Exploring page (step {step_num})…",
                    "screenshots": list(screenshots),
                },
                live_progress_writer,
            )

        try:
            agent = Agent(
                task=task,
                llm=self._llm(),
                browser_profile=make_browser_profile(),
                sensitive_data=sensitive_data,
                register_new_step_callback=_on_step,
                use_vision=True,
            )
            result = await agent.run(max_steps=UID_MAX_STEPS, on_step_end=_on_step_end)
        except Exception as exc:
            dur = int((datetime.utcnow() - start).total_seconds() * 1000)
            err_payload = {
                "status": "error",
                "percentage": 100,
                "current_step": "Discovery failed",
                "screenshots": list(screenshots),
                "error": str(exc),
                "duration_ms": dur,
            }
            await self._emit_progress(run_id, err_payload, live_progress_writer)
            return err_payload

        final_text = ""
        try:
            if hasattr(result, "final_result"):
                final_text = str(result.final_result()) or ""
            elif hasattr(result, "__str__"):
                final_text = str(result)
        except Exception:
            pass

        if final_text.strip().lower() in ("none", "null", "n/a", "{}", "[]", ""):
            final_text = ""

        raw_inventory = _parse_inventory_json(final_text)
        inventory: Optional[UiInventory] = None
        parse_error: Optional[str] = None
        if raw_inventory:
            try:
                if not raw_inventory.get("discovered_at"):
                    raw_inventory["discovered_at"] = datetime.utcnow().isoformat() + "Z"
                raw_inventory.setdefault("platform", "web")
                raw_inventory.setdefault("actor_role", actor_role)
                raw_inventory.setdefault("app_url", app_url)
                inventory = UiInventory.model_validate(raw_inventory)
            except Exception as exc:
                parse_error = f"Inventory validation failed: {exc}"
        else:
            parse_error = "Agent did not return parseable INVENTORY_JSON block."

        dur = int((datetime.utcnow() - start).total_seconds() * 1000)
        pages_count = len(inventory.pages) if inventory else 0

        if inventory:
            final_payload = {
                "status": "completed",
                "percentage": 100,
                "current_step": f"Discovery complete — {pages_count} pages",
                "screenshots": list(screenshots),
                "inventory": inventory.model_dump(),
                "pages_discovered": pages_count,
                "summary": f"Discovered {pages_count} pages across {len(inventory.navigation)} nav items.",
                "duration_ms": dur,
            }
        else:
            final_payload = {
                "status": "error",
                "percentage": 100,
                "current_step": "Discovery finished with errors",
                "screenshots": list(screenshots),
                "error": parse_error,
                "raw_output": final_text[:8000] if final_text else None,
                "duration_ms": dur,
            }

        await self._emit_progress(run_id, final_payload, live_progress_writer)
        return final_payload
