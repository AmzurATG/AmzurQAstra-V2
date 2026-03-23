"""
QAstra Logging Configuration

Log hierarchy:
    qastra                  -> logs/app.log         (combined, all categories)
    qastra.api              -> logs/api.log          (HTTP request/response)
    qastra.perf             -> logs/performance.log  (timing + slow request alerts)
    qastra.debug            -> logs/debug.log        (verbose debug output)
    qastra.exceptions       -> logs/exceptions.log   (errors + full tracebacks)
    qastra.security         -> logs/security.log     (auth, login, permission events)
    qastra.llm              -> logs/llm.log          (LLM provider calls, tokens, latency)
    qastra.integration      -> logs/integration.log  (Jira, Azure DevOps, Slack, Redmine)
    qastra.test             -> logs/test_execution.log (test run lifecycle)

Log files are written to QAstra/logs/ (outside backend/) so that uvicorn --reload
does not trigger restarts when log files are written to.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Category loggers: (logger_name, filename)
_LOG_CATEGORIES = [
    ("qastra.api",          "api.log"),
    ("qastra.perf",         "performance.log"),
    ("qastra.debug",        "debug.log"),
    ("qastra.exceptions",   "exceptions.log"),
    ("qastra.security",     "security.log"),
    ("qastra.llm",          "llm.log"),
    ("qastra.integration",  "integration.log"),
    ("qastra.test",         "test_execution.log"),
]

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Noisy third-party loggers to suppress unless DEBUG mode is on
_QUIET_LOGGERS = [
    "uvicorn.access",
    "uvicorn.error",
    "httpx",
    "httpcore",
    "multipart",
    "passlib",
]


def _make_rotating_handler(log_path: Path, max_bytes: int, backup_count: int) -> RotatingFileHandler:
    """Create a RotatingFileHandler with delay=True to avoid Windows file-lock issues."""
    handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,  # Only open the file on first write — reduces lock contention on Windows
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    return handler


def setup_logging() -> None:
    """
    Initialise the QAstra logging system. Call once at application startup.

    Idempotent — safe to call multiple times (e.g., during tests); subsequent
    calls are no-ops when handlers are already attached to the root qastra logger.
    """
    from config import settings  # Import here to avoid circular imports at module load

    root_logger = logging.getLogger("qastra")

    # Guard against double-initialisation (e.g., test environments calling setup twice)
    if root_logger.handlers:
        return

    # --- Resolve log directory (outside backend/ to avoid uvicorn --reload loops) ---
    log_dir = Path(settings.LOG_DIR).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # --- Root qastra logger: console + app.log (receives all propagated child records) ---
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    app_file_handler = _make_rotating_handler(
        log_dir / "app.log",
        settings.LOG_MAX_BYTES,
        settings.LOG_BACKUP_COUNT,
    )
    root_logger.addHandler(app_file_handler)

    # --- Category child loggers: each gets its own rotating file handler ---
    for logger_name, filename in _LOG_CATEGORIES:
        child = logging.getLogger(logger_name)
        # Inherit level from parent; propagate=True so records also reach app.log
        child.propagate = True
        child.addHandler(
            _make_rotating_handler(
                log_dir / filename,
                settings.LOG_MAX_BYTES,
                settings.LOG_BACKUP_COUNT,
            )
        )

    # --- Silence or dampen noisy third-party loggers ---
    for name in _QUIET_LOGGERS:
        noisy = logging.getLogger(name)
        if not settings.DEBUG:
            noisy.setLevel(logging.WARNING)
        noisy.propagate = False  # Don't flood app.log with uvicorn/httpx internals

    # Suppress SQLAlchemy query echo unless DB_ECHO is explicitly enabled
    if not settings.DB_ECHO:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").propagate = False

    root_logger.info(
        "Logging initialised | level=%s | log_dir=%s",
        settings.LOG_LEVEL,
        str(log_dir),
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger under the qastra hierarchy.

    Preferred names:
        get_logger("qastra.api")          # HTTP request logs
        get_logger("qastra.perf")         # Performance/timing logs
        get_logger("qastra.debug")        # Verbose debug logs
        get_logger("qastra.exceptions")   # Error + traceback logs
        get_logger("qastra.security")     # Auth / security event logs
        get_logger("qastra.llm")          # LLM call logs
        get_logger("qastra.integration")  # External integration logs
        get_logger("qastra.test")         # Test execution logs

    Any name that does NOT start with "qastra." is accepted but will not propagate
    to the qastra root and its records will not appear in app.log.
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Backward-compatible module-level alias
# Modules that previously did `from common.utils.logger import logger` continue
# to work without modification. The reference is resolved lazily after
# setup_logging() has been called.
# ---------------------------------------------------------------------------
logger = logging.getLogger("qastra")
