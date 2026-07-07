"""
Browser Engine Factory — selects the browser backend based on BROWSER_ENGINE config.

Supported engines:
  chrome  (default) — browser-use launches a local Chrome process.
  steel             — Steel.dev cloud browser; browser-use attaches via CDP websocket.

Callers receive a (BrowserContextKind, context) tuple.  They pattern-match on the
kind string to determine whether a cleanup step (SteelSession.release) is needed.

This is the single place in the codebase that reads settings.BROWSER_ENGINE.
Runners (TestCaseRunner, SharedSessionRunner) must not import config directly.
"""
from __future__ import annotations

import logging
from typing import Any, Literal, Optional, Tuple

from config import settings

logger = logging.getLogger(__name__)

# Discriminated union tag for the context object
BrowserContextKind = Literal["chrome", "steel"]


async def create_browser_context(
    *,
    run_id: str,
    headless: bool = False,
) -> Tuple[BrowserContextKind, Any]:
    """Create the appropriate browser context based on BROWSER_ENGINE.

    Args:
        run_id:   Identifier for logging / session tagging.
        headless: Whether the browser should run without a visible UI.
                  Ignored for the Steel engine (headless is always true there).

    Returns:
        A tuple of (kind, context):
          - ("chrome", None)         — use browser-use default local Chrome launch.
          - ("steel", SteelSession)  — connect to Steel CDP endpoint.

    Raises:
        SteelApiError: If BROWSER_ENGINE=steel but the Steel session cannot be created.
    """
    engine = (settings.BROWSER_ENGINE or "chrome").strip().lower()

    if engine == "steel":
        from features.functional.core.browser.steel_session_client import SteelSessionClient
        client = SteelSessionClient()
        session = await client.create_session(run_id=run_id)
        # Wait for the Steel container's Chrome process to be ready to accept
        # CDP commands.  Without this wait the WebSocket handshake succeeds
        # (the URL now includes the API key) but Chrome drops the connection
        # immediately ("message handler exited unexpectedly") because it hasn't
        # finished booting.  Typically ready within 2-5 s.
        await client.wait_for_session_ready(session.session_id)
        logger.info(
            "[BrowserEngineFactory] Steel session %s viewer=%s run=%s",
            session.session_id,
            session.viewer_url,
            run_id,
        )
        return ("steel", session)

    # Default: local Chrome managed by browser-use
    if engine != "chrome":
        logger.warning(
            "[BrowserEngineFactory] Unknown BROWSER_ENGINE=%r; falling back to 'chrome'.",
            engine,
        )
    return ("chrome", None)


async def release_browser_context(
    kind: BrowserContextKind,
    context: Any,
) -> None:
    """Release resources associated with a browser context.

    For Chrome contexts this is a no-op (browser-use manages lifecycle).
    For Steel contexts this terminates the remote session.

    Safe to call from a finally block — errors are logged, not raised.

    Args:
        kind:    The discriminator returned by create_browser_context.
        context: The context object returned by create_browser_context.
    """
    if kind == "steel" and context is not None:
        from features.functional.core.browser.steel_session_client import SteelSessionClient
        try:
            client = SteelSessionClient()
            await client.release_session(context.session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[BrowserEngineFactory] Steel session release failed: %s", exc)
