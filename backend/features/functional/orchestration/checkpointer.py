"""Postgres checkpointer singleton for LangGraph orchestration runs."""
from __future__ import annotations

from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from config import settings
from common.utils.logger import logger

_saver: Optional[AsyncPostgresSaver] = None
_setup_done = False
_conn_cm = None


def _sync_postgres_url(async_url: str) -> str:
    url = async_url.strip()
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://") :]
    if url.startswith("postgres+asyncpg://"):
        return "postgresql://" + url[len("postgres+asyncpg://") :]
    return url


async def get_checkpointer() -> Optional[AsyncPostgresSaver]:
    """Return a process-wide Postgres checkpointer (lazy init)."""
    global _saver, _setup_done, _conn_cm
    if _saver is not None:
        return _saver
    try:
        conn_string = _sync_postgres_url(settings.DATABASE_URL)
        _conn_cm = AsyncPostgresSaver.from_conn_string(conn_string)
        _saver = await _conn_cm.__aenter__()
        if not _setup_done:
            await _saver.setup()
            _setup_done = True
            logger.info("[Orchestration] LangGraph Postgres checkpointer ready")
        return _saver
    except Exception as exc:
        logger.warning(
            "[Orchestration] Postgres checkpointer unavailable: %s",
            exc,
        )
        return None


async def close_checkpointer() -> None:
    global _saver, _conn_cm, _setup_done
    if _conn_cm is not None:
        try:
            await _conn_cm.__aexit__(None, None, None)
        except Exception:
            pass
    _saver = None
    _conn_cm = None
    _setup_done = False
