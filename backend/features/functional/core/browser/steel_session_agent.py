"""
Policy layer for Steel session creation ("agent" without a separate runtime).

Chooses ``sessions.create`` kwargs from settings and optional run context so
integrity checks can use proxy + CAPTCHA solving when configured.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional

from common.utils.logger import logger
from config import settings


@dataclass
class SteelRunContext:
    """Optional hints for future adaptive policy (hostname, prior failures, etc.)."""

    target_url: Optional[str] = None


def build_steel_session_create_kwargs(context: Optional[SteelRunContext] = None) -> Dict[str, Any]:
    """
    Build kwargs for ``AsyncSteel.sessions.create``.

    Steel Method 2 features (solve_captcha, use_proxy) depend on your Steel plan.
    """
    ctx = context or SteelRunContext()
    kwargs: Dict[str, Any] = {
        "api_timeout": max(5_000, int(settings.STEEL_SESSION_API_TIMEOUT_MS)),
    }
    if settings.STEEL_SOLVE_CAPTCHA:
        kwargs["solve_captcha"] = True
    if settings.STEEL_USE_PROXY:
        kwargs["use_proxy"] = True

    extras: list[str] = []
    if ctx.target_url:
        extras.append(f"target={ctx.target_url[:80]!r}")

    logger.info(
        "[SteelAgent] sessions.create plan: solve_captcha=%s use_proxy=%s api_timeout_ms=%s %s",
        kwargs.get("solve_captcha", False),
        kwargs.get("use_proxy", False),
        kwargs["api_timeout"],
        (" ".join(extras) if extras else ""),
    )
    return kwargs
