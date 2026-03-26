"""
Steel Method 2: create a session via the official API, then connect with Playwright.

Falls back silently to Method 1 (API key only, no ``sessionId``) if ``steel-sdk``
is missing or the API call fails.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional

from common.utils.logger import logger


@dataclass
class ManagedSteelSession:
    session_id: str
    client: Any  # AsyncSteel — avoid import at module load when SDK absent


async def create_managed_steel_session(
    api_key: str,
    create_kwargs: Dict[str, Any],
) -> Optional[ManagedSteelSession]:
    """
    Create a Steel session and return its id + async client for ``sessions.release``.

    Caller must ``await client.sessions.release(session_id)`` and ``await client.close()``
    when finished (see PlaywrightRunner.close).
    """
    key = (api_key or "").strip()
    if not key:
        return None

    try:
        from steel import AsyncSteel
    except ImportError:
        logger.warning(
            "[Steel] steel-sdk not installed; using Steel Method 1 (connect URL only). "
            "Install with: uv pip install steel-sdk"
        )
        return None

    client = AsyncSteel(steel_api_key=key)
    try:
        session = await client.sessions.create(**create_kwargs)
        sid = getattr(session, "id", None)
        if not sid:
            logger.warning("[Steel] sessions.create returned no id; falling back to Method 1")
            await client.close()
            return None
        logger.info("[Steel] Intelligent session created id=%s", sid)
        return ManagedSteelSession(session_id=str(sid), client=client)
    except Exception as e:
        logger.warning("[Steel] Intelligent session create failed (%s); falling back to Method 1", e)
        try:
            await client.close()
        except Exception:
            pass
        return None


async def release_managed_steel_session(client: Any, session_id: str) -> None:
    if not client or not session_id:
        return
    try:
        await client.sessions.release(session_id)
        logger.info("[Steel] Released session %s", session_id)
    except Exception as e:
        logger.warning("[Steel] sessions.release failed for %s: %s", session_id, e)
    try:
        await client.close()
    except Exception:
        pass
