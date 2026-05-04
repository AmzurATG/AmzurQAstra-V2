"""
Alembic Environment Configuration for QAstra

Reads the database URL from the application's Settings and configures
Alembic to use the SQLAlchemy metadata from all registered models.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# ---------------------------------------------------------------------------
# Ensure the backend package root is on sys.path so that ``config``,
# ``common.*``, and ``features.*`` are importable.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings  # noqa: E402
from common.db.base import Base  # noqa: E402

# Import ALL models so that Base.metadata is fully populated.
import common.db.models  # noqa: E402,F401 — registers common models
import features.functional.db.models.requirement  # noqa: E402,F401
import features.functional.db.models.test_case  # noqa: E402,F401
import features.functional.db.models.test_step  # noqa: E402,F401
import features.functional.db.models.test_run  # noqa: E402,F401
import features.functional.db.models.test_result  # noqa: E402,F401
import features.functional.db.models.gap_analysis_run  # noqa: E402,F401
import features.functional.db.models.test_recommendation_run  # noqa: E402,F401

# Alembic Config object (provides access to alembic.ini values)
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Override sqlalchemy.url from application settings (sync driver required)
# ---------------------------------------------------------------------------
db_url = settings.DATABASE_URL
# Alembic needs a synchronous driver
if "asyncpg" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
elif not db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=settings.DB_SCHEMA,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Create the target schema if it doesn't exist
        schema = settings.DB_SCHEMA
        connection.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        )
        # Set search_path to ONLY the target schema so that
        # CREATE TABLE/TYPE IF NOT EXISTS checks don't find
        # objects in other schemas and skip creation.
        connection.execute(
            text(f"SET search_path TO {schema}")
        )
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
