"""Shared browser-use BrowserProfile for integrity check, UI discovery, and test runs."""
from __future__ import annotations

from typing import Optional

from config import settings
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args


def make_browser_profile(*, headless: Optional[bool] = None):
    """
    Build a BrowserProfile consistent across BIC, UI discovery, and test execution.

    Default headless=False so Chrome opens visibly (MFA, SSO, manual login).
    Override via BROWSER_USE_HEADLESS in .env or pass headless= explicitly.
    """
    from browser_use import BrowserProfile

    if headless is None:
        headless = settings.BROWSER_USE_HEADLESS

    return BrowserProfile(
        headless=headless,
        is_local=True,
        disable_security=True,
        args=default_browser_chrome_args(),
        enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
    )
