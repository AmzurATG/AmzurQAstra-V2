"""
Abstract Browser Runner Interface

Every browser engine (Playwright, Steel, etc.) must implement this interface
so the rest of the application is decoupled from the underlying engine.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StepActionResult:
    """Result returned by every browser action."""
    success: bool
    error: Optional[str] = None
    # Base64-encoded PNG screenshot captured after the action (when requested)
    screenshot_b64: Optional[str] = None
    # Full page HTML — populated only when requested (e.g. for login form detection)
    page_html: Optional[str] = None
    # URL of the page after the action completes
    current_url: Optional[str] = None
    # Extra metadata from the engine
    metadata: dict = field(default_factory=dict)


class BrowserRunner(ABC):
    """
    Abstract base for browser automation engines.

    Implementations must be usable as async context managers:

        async with get_browser_runner() as runner:
            await runner.navigate("https://example.com")
    """

    # ------------------------------------------------------------------
    # Context manager support — engines must launch/close in __aenter__/__aexit__
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "BrowserRunner":
        await self.start()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    @abstractmethod
    async def start(self) -> None:
        """Launch the browser and create an initial page."""

    @abstractmethod
    async def close(self) -> None:
        """Close the browser and release all resources."""

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    @abstractmethod
    async def navigate(self, url: str) -> StepActionResult:
        """Navigate to a URL and wait for the page to load."""

    # ------------------------------------------------------------------
    # Page interaction
    # ------------------------------------------------------------------

    @abstractmethod
    async def click(self, selector: str) -> StepActionResult:
        """Click an element identified by a CSS or text selector."""

    @abstractmethod
    async def fill(self, selector: str, value: str) -> StepActionResult:
        """Clear and fill an input field."""

    @abstractmethod
    async def select_option(self, selector: str, value: str) -> StepActionResult:
        """Select a <select> dropdown option by value."""

    @abstractmethod
    async def hover(self, selector: str) -> StepActionResult:
        """Hover the mouse over an element."""

    @abstractmethod
    async def wait(self, milliseconds: int) -> StepActionResult:
        """Pause execution for a fixed number of milliseconds."""

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    async def is_visible(self, selector: str) -> bool:
        """Instant check — is the element currently visible? Does NOT wait."""
        result = await self.assert_visible(selector)
        return result.success

    @abstractmethod
    async def assert_visible(self, selector: str) -> StepActionResult:
        """Assert that an element is visible on the page (waits up to timeout)."""

    @abstractmethod
    async def assert_text(self, selector: str, expected: str) -> StepActionResult:
        """Assert that an element contains the expected text."""

    @abstractmethod
    async def assert_url(self, expected: str) -> StepActionResult:
        """Assert that the current URL contains the expected string."""

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @abstractmethod
    async def screenshot(self, path: Optional[str] = None) -> StepActionResult:
        """
        Take a screenshot.
        If path is given, save the PNG to that filesystem path.
        Always returns base64-encoded PNG in screenshot_b64.
        """

    @abstractmethod
    async def get_page_html(self) -> str:
        """Return the full outer HTML of the current page."""

    @abstractmethod
    async def get_current_url(self) -> str:
        """Return the current page URL."""

    # ------------------------------------------------------------------
    # Session state (for OAuth replay)
    # ------------------------------------------------------------------

    @abstractmethod
    async def load_storage_state(self, state: dict) -> None:
        """Apply a saved Playwright storageState dict to the current context."""

    @abstractmethod
    async def save_storage_state(self) -> dict:
        """Capture and return the current browser storageState as a dict."""

    # ------------------------------------------------------------------
    # Network observation (optional — engines may no-op)
    # ------------------------------------------------------------------

    async def start_network_logging(self) -> None:
        """Begin capturing request/response metadata for diagnostics."""
        return None

    async def clear_network_log(self) -> None:
        """Clear the in-memory network log."""
        return None

    async def get_network_log_summary(self, limit: int = 50) -> str:
        """Human-readable summary of recent network activity (truncated)."""
        return ""

    async def wait_for_post_oauth_app_page(self, app_url: str, timeout_ms: int = 90_000) -> bool:
        """
        After an in-page SSO click, poll all open tabs for a URL on the app host that is
        not the login screen. Playwright implements this; other engines return False.
        """
        return False

    async def focus_page_url_contains(self, fragment: str, timeout_ms: int = 60_000) -> bool:
        """
        Switch the active page to the first open tab whose URL contains ``fragment``
        (case-insensitive). Used for Google SSO flows. Playwright implements this.
        """
        return False
