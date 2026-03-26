"""
Central rules for when QAstra uses local Chromium vs Steel (Playwright over CDP).

- ``BROWSER_ENGINE=steel`` → always use Steel when ``STEEL_API_KEY`` is set.
- ``BROWSER_ENGINE=playwright`` + ``STEEL_USE_WITH_PLAYWRIGHT=true`` + key → Steel.
- ``BROWSER_ENGINE=playwright`` + flag false or no key → local Playwright only.
"""
from typing import Optional

from config import settings


def steel_cdp_enabled_for_engine(engine: Optional[str]) -> bool:
    """
    Return True if the given engine choice should connect via Steel CDP.

    ``engine`` is typically ``playwright`` or ``steel`` (from request or config).
    """
    if not (settings.STEEL_API_KEY or "").strip():
        return False

    chosen = (engine or settings.BROWSER_ENGINE or "playwright").lower()
    if chosen == "steel":
        return True
    if chosen == "playwright" and settings.STEEL_USE_WITH_PLAYWRIGHT:
        return True
    return False


def resolve_runner_engine(request_engine: Optional[str] = None) -> str:
    """Effective engine string after applying request override or config default."""
    if request_engine and request_engine.strip():
        return request_engine.strip().lower()
    return (settings.BROWSER_ENGINE or "playwright").lower()


def effective_browser_label(request_engine: Optional[str] = None) -> str:
    """
    Short label for persistence / UI: ``steel`` when using Steel CDP, else ``playwright``.
    """
    eng = resolve_runner_engine(request_engine)
    if steel_cdp_enabled_for_engine(eng):
        return "steel"
    return "playwright"


def require_steel_key_if_steel_engine(engine: Optional[str]) -> None:
    """Raise ValueError if user chose steel without an API key."""
    eng = (engine or "").lower()
    if eng == "steel" and not (settings.STEEL_API_KEY or "").strip():
        raise ValueError(
            "BROWSER_ENGINE=steel requires STEEL_API_KEY. "
            "Set it in the environment or use BROWSER_ENGINE=playwright for local Chromium."
        )
