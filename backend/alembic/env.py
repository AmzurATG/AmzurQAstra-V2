"""
Alembic Environment Configuration for QAstra

Reads the database URL from the application's Settings and configures
Alembic to use the SQLAlchemy metadata from all registered models.

If no .env file exists, prompts for database credentials interactively.
"""
import getpass
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Ensure the backend package root is on sys.path so that ``config``,
# ``common.*``, and ``features.*`` are importable.
# ---------------------------------------------------------------------------
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from config import settings  # noqa: E402
from common.db.base import Base  # noqa: E402

# Import ALL models so that Base.metadata is fully populated.
import common.db.models  # noqa: E402,F401 — registers common models
import features.functional.db.models.requirement  # noqa: E402,F401
import features.functional.db.models.test_case  # noqa: E402,F401
import features.functional.db.models.test_step  # noqa: E402,F401
import features.functional.db.models.test_run  # noqa: E402,F401
import features.functional.db.models.test_result  # noqa: E402,F401

# Alembic Config object (provides access to alembic.ini values)
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Resolve database URL — use .env if available, otherwise prompt
# ---------------------------------------------------------------------------
_env_file = backend_dir / ".env"
_default_url = "postgresql://postgres:postgres@localhost:5432/qastra"

db_url = settings.DATABASE_URL

# Normalise to sync driver for Alembic
if "asyncpg" in db_url:
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

# If there is no .env file and the URL is still the hard-coded default,
# prompt the user interactively for database credentials.
if not _env_file.exists() and db_url == _default_url:
    print()
    print("=" * 55)
    print("  No .env file found — enter database credentials")
    print("=" * 55)
    print()
    db_user = input("  Database username [qastra]: ").strip() or "qastra"
    db_pass = getpass.getpass("  Database password [qastra123]: ") or "qastra123"
    db_host = input("  Database host [localhost]: ").strip() or "localhost"
    db_port = input("  Database port [5432]: ").strip() or "5432"
    db_name = input("  Database name [qastra]: ").strip() or "qastra"
    db_url = f"postgresql://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}"
    print()

config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
