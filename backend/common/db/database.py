"""
SQLAlchemy Database Configuration
"""
import ssl
from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from config import settings

_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Supabase (and most cloud Postgres) requires SSL connections.
_is_cloud = "supabase.com" in _db_url or "supabase.co" in _db_url
_connect_args = {}
if _is_cloud:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    _connect_args["ssl"] = ssl_ctx

# Create async engine
# Use connection pooling for cloud databases (avoids expensive TCP+SSL handshake per request).
# Keep NullPool for local dev where connections are cheap.
_pool_kwargs = (
    {"pool_size": 5, "max_overflow": 10, "pool_recycle": 300, "pool_pre_ping": True}
    if _is_cloud
    else {"poolclass": NullPool}
)

engine = create_async_engine(
    _db_url,
    echo=settings.DB_ECHO,
    connect_args=_connect_args,
    **_pool_kwargs,
)


# Set search_path to the configured schema on every new connection
@event.listens_for(engine.sync_engine, "connect")
def _set_search_path(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {settings.DB_SCHEMA}")
    cursor.close()


# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def create_background_session_maker():
    """Create an isolated engine + session maker for background threads that run
    their own event loop (e.g. Windows ProactorEventLoop for Playwright).
    Uses NullPool so connections are never shared across loops."""
    bg_engine = create_async_engine(
        _db_url,
        echo=settings.DB_ECHO,
        connect_args=_connect_args,
        poolclass=NullPool,
    )

    @event.listens_for(bg_engine.sync_engine, "connect")
    def _set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {settings.DB_SCHEMA}")
        cursor.close()

    maker = async_sessionmaker(
        bg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return maker, bg_engine


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
