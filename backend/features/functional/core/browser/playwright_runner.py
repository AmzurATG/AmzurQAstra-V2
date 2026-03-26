"""
Playwright Browser Runner

Drives a real Chromium browser directly from Python using the official
playwright.async_api library — no external Node.js process required.

Features:
- Async-native, compatible with FastAPI's asyncio event loop
- Per-step screenshots saved to filesystem + returned as base64
- Stealth-friendly options (no webdriver flag, natural viewport)
- Full storage_state replay for OAuth (new context with saved state)
- Optional network response logging for LLM diagnostics
- Windows compatibility: automatic ProactorEventLoop bridge when the
  running loop (e.g. uvicorn's SelectorEventLoop) cannot spawn subprocesses
"""
import asyncio
import base64
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from features.functional.core.browser.base import BrowserRunner, StepActionResult
from features.functional.core.browser.steel_cdp_session import build_steel_cdp_url
from features.functional.core.browser.steel_intelligent_session import (
    create_managed_steel_session,
    release_managed_steel_session,
)
from features.functional.core.browser.steel_session_agent import (
    SteelRunContext,
    build_steel_session_create_kwargs,
)
from common.utils.logger import logger
from config import settings


def _needs_proactor_bridge() -> bool:
    """On Windows, SelectorEventLoop cannot spawn subprocesses (Playwright needs this)."""
    if sys.platform != "win32":
        return False
    try:
        loop = asyncio.get_running_loop()
        return not isinstance(loop, asyncio.ProactorEventLoop)
    except RuntimeError:
        return False


class PlaywrightRunner(BrowserRunner):
    """
    Browser runner backed by Python Playwright (Chromium).

    Lifecycle:
        async with PlaywrightRunner(headless=True) as runner:
            await runner.navigate("https://example.com")
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        viewport: Optional[dict] = None,
        *,
        connect_via_steel: bool = False,
        steel_api_key: str = "",
        steel_session_id: Optional[str] = None,
        steel_target_url: Optional[str] = None,
    ):
        self._headless = headless
        self._browser_type = browser_type
        self._viewport = viewport or {"width": 1280, "height": 800}
        self._connect_via_steel = connect_via_steel
        self._steel_api_key = steel_api_key or ""
        self._steel_session_id = steel_session_id
        self._steel_target_url = (steel_target_url or "").strip() or None
        self._steel_managed_session_id: Optional[str] = None
        self._steel_sdk_client: Any = None

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self._proactor_loop: Optional[asyncio.ProactorEventLoop] = None
        self._proactor_thread: Optional[threading.Thread] = None

        self._network_logging_enabled: bool = False
        self._network_entries: List[str] = []
        self._net_listener_page: Optional[Page] = None
        self._response_handler = None

    def _action_timeout(self) -> int:
        return settings.BROWSER_DEFAULT_TIMEOUT_MS

    def _new_context_options(self, storage_state: Optional[Any] = None) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "viewport": self._viewport,
            "ignore_https_errors": True,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        }
        if storage_state is not None:
            opts["storage_state"] = storage_state
        return opts

    # ------------------------------------------------------------------
    # ProactorEventLoop bridge (Windows + uvicorn --reload workaround)
    # ------------------------------------------------------------------

    async def _pw(self, coro):
        """Run a Playwright coroutine, bridging to the ProactorEventLoop when needed."""
        if self._proactor_loop is not None:
            future = asyncio.run_coroutine_threadsafe(coro, self._proactor_loop)
            return await asyncio.wrap_future(future)
        return await coro

    def _start_proactor_bridge(self) -> None:
        self._proactor_loop = asyncio.ProactorEventLoop()
        self._proactor_thread = threading.Thread(
            target=self._proactor_loop.run_forever, daemon=True
        )
        self._proactor_thread.start()
        logger.info("[Browser] Started ProactorEventLoop bridge for Windows")

    def _stop_proactor_bridge(self) -> None:
        if self._proactor_loop is not None:
            self._proactor_loop.call_soon_threadsafe(self._proactor_loop.stop)
            if self._proactor_thread:
                self._proactor_thread.join(timeout=5)
            self._proactor_loop.close()
            self._proactor_loop = None
            self._proactor_thread = None

    def _make_response_handler(self):
        def on_response(response):
            if not self._network_logging_enabled:
                return
            try:
                req = response.request
                url = req.url
                line = f"{req.method} {response.status} {url[:400]}"
                if len(self._network_entries) >= 500:
                    self._network_entries.pop(0)
                self._network_entries.append(line)
            except Exception:
                pass

        return on_response

    async def _bind_network_listener(self) -> None:
        if not self._network_logging_enabled or not self._page:
            return
        if self._net_listener_page is self._page:
            return
        self._response_handler = self._make_response_handler()

        async def _register():
            self._page.on("response", self._response_handler)

        await self._pw(_register())
        self._net_listener_page = self._page

    async def start_network_logging(self) -> None:
        self._network_logging_enabled = True
        self._network_entries = []
        await self._bind_network_listener()

    async def clear_network_log(self) -> None:
        self._network_entries = []

    async def get_network_log_summary(self, limit: int = 50) -> str:
        if not self._network_entries:
            return "(no network entries captured)"
        lines = self._network_entries[-limit:]
        return "\n".join(lines)

    async def _apply_default_timeout(self) -> None:
        async def _apply():
            self._page.set_default_timeout(self._action_timeout())

        await self._pw(_apply())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if _needs_proactor_bridge():
            self._start_proactor_bridge()

        self._playwright = await self._pw(async_playwright().start())
        if self._connect_via_steel:
            await self._start_steel_playwright()
        else:
            launcher = getattr(self._playwright, self._browser_type)
            self._browser = await self._pw(launcher.launch(
                headless=self._headless,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            ))
            self._context = await self._pw(
                self._browser.new_context(**self._new_context_options())
            )
            self._page = await self._pw(self._context.new_page())

        await self._apply_default_timeout()
        mode = "steel_cdp" if self._connect_via_steel else self._browser_type
        logger.info(f"[Browser] Playwright started (headless={self._headless}, {mode})")

    async def _start_steel_playwright(self) -> None:
        """Steel cloud browser via CDP (Method 1 or Method 2 + intelligent session)."""
        api_key = self._steel_api_key
        session_id = (self._steel_session_id or "").strip() or None
        self._steel_managed_session_id = None
        self._steel_sdk_client = None

        want_intel = bool(settings.STEEL_INTELLIGENT_SESSIONS and session_id is None)
        if want_intel:
            agent_ctx = SteelRunContext(target_url=self._steel_target_url)
            skwargs = build_steel_session_create_kwargs(agent_ctx)
            managed = await create_managed_steel_session(api_key, skwargs)
            if managed:
                session_id = managed.session_id
                self._steel_managed_session_id = managed.session_id
                self._steel_sdk_client = managed.client

        cdp_url = build_steel_cdp_url(api_key, session_id)
        try:
            self._browser = await self._pw(
                self._playwright.chromium.connect_over_cdp(cdp_url)
            )
        except Exception:
            if self._steel_managed_session_id and self._steel_sdk_client:
                await release_managed_steel_session(
                    self._steel_sdk_client,
                    self._steel_managed_session_id,
                )
                self._steel_managed_session_id = None
                self._steel_sdk_client = None
            raise

        if self._browser.contexts:
            self._context = self._browser.contexts[0]
        else:
            self._context = await self._pw(
                self._browser.new_context(**self._new_context_options())
            )

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._pw(self._context.new_page())

        logger.info(
            "[Browser] Steel CDP connected sessionId=%s managed_release=%s",
            session_id or "auto",
            bool(self._steel_managed_session_id),
        )

    async def close(self) -> None:
        try:
            if self._connect_via_steel:
                if self._browser:
                    await self._pw(self._browser.close())
                if self._steel_managed_session_id and self._steel_sdk_client:
                    await release_managed_steel_session(
                        self._steel_sdk_client,
                        self._steel_managed_session_id,
                    )
            else:
                if self._context:
                    await self._pw(self._context.close())
                if self._browser:
                    await self._pw(self._browser.close())
            if self._playwright:
                await self._pw(self._playwright.stop())
        except Exception as e:
            logger.warning(f"[Browser] Error during close: {e}")
        finally:
            self._page = self._context = self._browser = self._playwright = None
            self._net_listener_page = None
            self._response_handler = None
            self._steel_managed_session_id = None
            self._steel_sdk_client = None
            self._stop_proactor_bridge()
        logger.info("[Browser] Playwright closed")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    async def navigate(self, url: str) -> StepActionResult:
        wait_until = settings.BROWSER_NAVIGATION_WAIT_UNTIL
        timeout = settings.BROWSER_NAVIGATION_TIMEOUT_MS
        retries = max(1, settings.BROWSER_NAVIGATION_RETRIES)
        backoff_s = settings.BROWSER_NAVIGATION_RETRY_BACKOFF_MS / 1000.0
        last_err: Optional[Exception] = None

        for attempt in range(retries):
            try:
                response = await self._pw(
                    self._page.goto(url, wait_until=wait_until, timeout=timeout)
                )
                current_url = await self._pw(self._get_url())
                reachable = True
                err_detail = None
                if response is not None and response.status >= 400:
                    reachable = False
                    err_detail = f"HTTP {response.status}"
                return StepActionResult(
                    success=reachable,
                    current_url=current_url,
                    error=err_detail,
                )
            except Exception as e:
                last_err = e
                logger.warning(f"[Browser] navigate attempt {attempt + 1}/{retries} ({url}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_s)

        logger.error(f"[Browser] navigate({url}) failed after {retries} attempts")
        return StepActionResult(success=False, error=str(last_err) if last_err else "navigation failed")

    # ------------------------------------------------------------------
    # Page interaction
    # ------------------------------------------------------------------

    async def click(self, selector: str) -> StepActionResult:
        try:
            await self._pw(self._page.click(selector, timeout=self._action_timeout()))
            current_url = await self._pw(self._get_url())
            return StepActionResult(success=True, current_url=current_url)
        except Exception as e:
            logger.error(f"[Browser] click({selector}): {e}")
            return StepActionResult(success=False, error=str(e))

    async def fill(self, selector: str, value: str) -> StepActionResult:
        try:
            await self._pw(self._page.fill(selector, value, timeout=self._action_timeout()))
            return StepActionResult(success=True)
        except Exception as e:
            logger.error(f"[Browser] fill({selector}): {e}")
            return StepActionResult(success=False, error=str(e))

    async def select_option(self, selector: str, value: str) -> StepActionResult:
        try:
            await self._pw(self._page.select_option(selector, value, timeout=self._action_timeout()))
            return StepActionResult(success=True)
        except Exception as e:
            logger.error(f"[Browser] select_option({selector}): {e}")
            return StepActionResult(success=False, error=str(e))

    async def hover(self, selector: str) -> StepActionResult:
        try:
            await self._pw(self._page.hover(selector, timeout=self._action_timeout()))
            return StepActionResult(success=True)
        except Exception as e:
            logger.error(f"[Browser] hover({selector}): {e}")
            return StepActionResult(success=False, error=str(e))

    async def wait(self, milliseconds: int) -> StepActionResult:
        try:
            await self._pw(self._page.wait_for_timeout(milliseconds))
            return StepActionResult(success=True)
        except Exception as e:
            return StepActionResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    async def is_visible(self, selector: str) -> bool:
        """Instant DOM check — no wait timeout."""
        try:
            async def _check():
                return await self._page.is_visible(selector)

            return await self._pw(_check())
        except Exception:
            return False

    async def assert_visible(self, selector: str) -> StepActionResult:
        try:
            await self._pw(
                self._page.wait_for_selector(selector, state="visible", timeout=self._action_timeout())
            )
            return StepActionResult(success=True)
        except Exception as e:
            return StepActionResult(success=False, error=f"Element not visible: {selector} — {e}")

    async def assert_text(self, selector: str, expected: str) -> StepActionResult:
        try:
            async def _inner_text():
                locator = self._page.locator(selector)
                return await locator.inner_text(timeout=self._action_timeout())

            actual = await self._pw(_inner_text())
            if expected.lower() in actual.lower():
                return StepActionResult(success=True)
            return StepActionResult(
                success=False,
                error=f"Expected '{expected}' in text but got '{actual[:100]}'",
            )
        except Exception as e:
            return StepActionResult(success=False, error=str(e))

    async def assert_url(self, expected: str) -> StepActionResult:
        current = await self._pw(self._get_url())
        if expected.lower() in current.lower():
            return StepActionResult(success=True, current_url=current)
        return StepActionResult(
            success=False,
            current_url=current,
            error=f"URL '{current}' does not contain '{expected}'",
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    async def _get_url(self) -> str:
        """Read page.url — a coroutine wrapper so it can be dispatched to the bridge."""
        return self._page.url if self._page else ""

    async def screenshot(self, path: Optional[str] = None) -> StepActionResult:
        try:
            if path:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                await self._pw(self._page.screenshot(path=path, full_page=False))
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
            else:
                raw = await self._pw(self._page.screenshot(full_page=False))
                b64 = base64.b64encode(raw).decode()
            current_url = await self._pw(self._get_url())
            return StepActionResult(success=True, screenshot_b64=b64, current_url=current_url)
        except Exception as e:
            logger.error(f"[Browser] screenshot: {e}")
            return StepActionResult(success=False, error=str(e))

    async def get_page_html(self) -> str:
        try:
            return await self._pw(self._page.content())
        except Exception:
            return ""

    async def get_current_url(self) -> str:
        return await self._pw(self._get_url())

    async def wait_for_post_oauth_app_page(self, app_url: str, timeout_ms: int = 90_000) -> bool:
        """
        Poll every context tab: after Google SSO, OAuth may use a popup while the
        original tab stays on /login. Adopt the first tab that shows the app host
        without an active login password field.
        """
        try:
            target_host = (urlparse(app_url).hostname or "").lower()
        except Exception:
            return False
        if not target_host or not self._browser:
            return False

        def _host_ok(hostname: Optional[str]) -> bool:
            if not hostname:
                return False
            h = hostname.lower()
            return h == target_host or h.endswith("." + target_host)

        deadline = time.monotonic() + max(5_000, timeout_ms) / 1000.0

        async def _pages_with_context() -> List[Tuple[BrowserContext, Page]]:
            out: List[Tuple[BrowserContext, Page]] = []
            if self._connect_via_steel and self._browser:
                for ctx in list(self._browser.contexts):
                    for p in list(ctx.pages):
                        out.append((ctx, p))
            elif self._context:
                for p in list(self._context.pages):
                    out.append((self._context, p))
            return out

        async def _try_adopt() -> bool:
            for ctx, p in await _pages_with_context():
                try:
                    url = (p.url or "").strip()
                    if not url or url.startswith("about:"):
                        continue
                    pu = urlparse(url)
                    if not _host_ok(pu.hostname):
                        continue
                    path = (pu.path or "").lower()
                    url_low = url.lower()
                    loginish = any(
                        seg in path or seg in url_low
                        for seg in ("/login", "/signin", "/sign-in")
                    )
                    if loginish:
                        try:
                            pwd = await p.is_visible('input[type="password"]')
                        except Exception:
                            pwd = True
                        if pwd:
                            continue
                    self._context = ctx
                    self._page = p
                    await p.bring_to_front()
                    await self._apply_default_timeout()
                    self._net_listener_page = None
                    await self._bind_network_listener()
                    logger.info(f"[Browser] Active tab switched after SSO: {url}")
                    return True
                except Exception:
                    continue
            return False

        while time.monotonic() < deadline:
            if await self._pw(_try_adopt()):
                return True
            await asyncio.sleep(1.5)

        logger.warning(
            f"[Browser] No authenticated app tab detected within {timeout_ms}ms (checked all windows)"
        )
        return False

    async def focus_page_url_contains(self, fragment: str, timeout_ms: int = 60_000) -> bool:
        """Activate the first tab whose URL contains ``fragment`` (case-insensitive)."""
        if not fragment or not self._browser:
            return False
        frag_l = fragment.lower()
        deadline = time.monotonic() + max(3_000, timeout_ms) / 1000.0

        async def _pages_with_context() -> List[Tuple[BrowserContext, Page]]:
            out: List[Tuple[BrowserContext, Page]] = []
            if self._connect_via_steel and self._browser:
                for ctx in list(self._browser.contexts):
                    for p in list(ctx.pages):
                        out.append((ctx, p))
            elif self._context:
                for p in list(self._context.pages):
                    out.append((self._context, p))
            return out

        while time.monotonic() < deadline:
            for ctx, p in await _pages_with_context():
                try:
                    url = (p.url or "").lower()
                    if frag_l not in url:
                        continue
                    self._context = ctx
                    self._page = p
                    await p.bring_to_front()
                    await self._apply_default_timeout()
                    self._net_listener_page = None
                    await self._bind_network_listener()
                    logger.info("[Browser] Focused tab matching %r: %s", fragment, p.url)
                    return True
                except Exception:
                    continue
            await asyncio.sleep(0.45)

        logger.warning("[Browser] No tab found with URL containing %r within %sms", fragment, timeout_ms)
        return False

    # ------------------------------------------------------------------
    # Session state — full Playwright storage_state on a fresh context
    # ------------------------------------------------------------------

    async def load_storage_state(self, state: dict) -> None:
        if not self._browser:
            logger.warning("[Browser] load_storage_state: browser not started")
            return
        try:
            if self._connect_via_steel:
                new_ctx = await self._pw(
                    self._browser.new_context(**self._new_context_options(storage_state=state))
                )
                new_page = await self._pw(new_ctx.new_page())
                old_ctx = self._context
                self._context = new_ctx
                self._page = new_page
                try:
                    if old_ctx is not None and old_ctx != new_ctx:
                        await self._pw(old_ctx.close())
                except Exception as ex:
                    logger.warning(f"[Browser] Could not close previous Steel context: {ex}")
                await self._apply_default_timeout()
                self._net_listener_page = None
                await self._bind_network_listener()
                logger.info("[Browser] Storage state applied (Steel: new context + page)")
                return

            if self._context:
                await self._pw(self._context.close())
            self._context = await self._pw(
                self._browser.new_context(**self._new_context_options(storage_state=state))
            )
            self._page = await self._pw(self._context.new_page())
            await self._apply_default_timeout()
            self._net_listener_page = None
            await self._bind_network_listener()
            logger.info("[Browser] Storage state applied via new browser context")
        except Exception as e:
            logger.warning(f"[Browser] Failed to load storage state: {e}")
            raise

    async def save_storage_state(self) -> dict:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                tmp_path = f.name
            await self._pw(self._context.storage_state(path=tmp_path))
            with open(tmp_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[Browser] Failed to save storage state: {e}")
            return {}
