"""Shared Chrome CLI flags for browser-use BrowserProfile (local automation)."""
from __future__ import annotations

from typing import List

from config import settings


def default_browser_chrome_args() -> List[str]:
    """
    Defaults aligned across functional runs and integrity check.
    Suppresses native Chrome password-leak / breach warnings that are not JS dialogs
    (PopupsWatchdog only handles alert/confirm/prompt).
    """
    args: List[str] = [
        "--disable-save-password-bubble",
        "--disable-autofill",
        "--disable-notifications",
        "--disable-infobars",
        "--no-default-browser-check",
        "--no-first-run",
        "--disable-features=PasswordLeakDetection",
    ]
    extra = settings.BROWSER_CHROME_EXTRA_ARGS
    if extra:
        args.extend(p.strip() for p in extra.split(",") if p.strip())
    return args
