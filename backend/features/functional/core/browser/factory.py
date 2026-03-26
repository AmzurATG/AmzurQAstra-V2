"""
Browser Runner Factory

Returns PlaywrightRunner, optionally connected to Steel via CDP when
``STEEL_API_KEY`` is set and engine policy allows it (see ``browser_engine_policy``).
"""
from typing import Optional

from features.functional.core.browser.base import BrowserRunner
from features.functional.core.browser.browser_engine_policy import (
    require_steel_key_if_steel_engine,
    resolve_runner_engine,
    steel_cdp_enabled_for_engine,
)
from config import settings


def get_browser_runner(
    headless: bool = True,
    engine: Optional[str] = None,
    steel_target_url: Optional[str] = None,
) -> BrowserRunner:
    """
    Return a BrowserRunner (always Playwright-backed; Steel uses connect_over_cdp).

    Args:
        headless: Ignored for Steel cloud browsers (Steel controls visibility).
        engine:   Override ``BROWSER_ENGINE`` (``playwright`` | ``steel``).
        steel_target_url: Optional app URL for Steel session policy logging (e.g. integrity check target).

    Raises:
        ValueError: If engine is ``steel`` but ``STEEL_API_KEY`` is missing.
    """
    resolved = resolve_runner_engine(engine)
    require_steel_key_if_steel_engine(resolved)

    use_steel_cdp = steel_cdp_enabled_for_engine(resolved)
    api_key = (settings.STEEL_API_KEY or "").strip()

    from features.functional.core.browser.playwright_runner import PlaywrightRunner

    return PlaywrightRunner(
        headless=headless,
        connect_via_steel=use_steel_cdp,
        steel_api_key=api_key,
        steel_target_url=steel_target_url,
    )
