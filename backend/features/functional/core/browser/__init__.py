"""
Browser automation module.

Provides a unified BrowserRunner interface via :class:`PlaywrightRunner`:
local Chromium, or Steel cloud browsers through ``chromium.connect_over_cdp``
(see ``steel_cdp_session`` and ``browser_engine_policy``).

Usage:
    from features.functional.core.browser.factory import get_browser_runner
    async with get_browser_runner() as runner:
        await runner.navigate("https://example.com")
"""
from features.functional.core.browser.base import BrowserRunner, StepActionResult
from features.functional.core.browser.factory import get_browser_runner

__all__ = ["BrowserRunner", "StepActionResult", "get_browser_runner"]
