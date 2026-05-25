# Logging Implementation Guide

A reusable, production-grade logging pattern extracted from the QAstra backend.  
This document covers configuration, implementation, and how to adapt the approach to any Python + FastAPI project.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Principles](#design-principles)
3. [File Structure](#file-structure)
4. [Step-by-Step Implementation](#step-by-step-implementation)
   - [4.1 Settings (config.py)](#41-settings-configpy)
   - [4.2 Logger Module (logger.py)](#42-logger-module-loggerpy)
   - [4.3 HTTP Middleware (logging_middleware.py)](#43-http-middleware-logging_middlewarepy)
   - [4.4 Application Startup (main.py)](#44-application-startup-mainpy)
   - [4.5 Using Loggers in Business Code](#45-using-loggers-in-business-code)
5. [Log File Output](#log-file-output)
6. [Customizing for Your Project](#customizing-for-your-project)
7. [Platform Considerations (Windows)](#platform-considerations-windows)
8. [Production Best Practices](#production-best-practices)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Application Code                         │
│  get_logger("myapp.api") / get_logger("myapp.llm") / etc.       │
└─────────────────────────────┬───────────────────────────────────┘
                              │ log records propagate upward
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Root Logger: "myapp"                               │
│  Handlers: StreamHandler(stdout) + RotatingFileHandler(app.log)  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ child loggers propagate=True
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│  Child Loggers (each with its own RotatingFileHandler)            │
│                                                                   │
│  myapp.api          →  logs/api.log                               │
│  myapp.perf         →  logs/performance.log                       │
│  myapp.exceptions   →  logs/exceptions.log                        │
│  myapp.security     →  logs/security.log                          │
│  myapp.llm          →  logs/llm.log                               │
│  myapp.integration  →  logs/integration.log                       │
│  myapp.debug        →  logs/debug.log                             │
│  myapp.test         →  logs/test_execution.log                    │
└───────────────────────────────────────────────────────────────────┘
```

**Key idea:** Every child logger writes to its own dedicated file *and* propagates to the root logger's `app.log`. This gives you both a combined log (for general troubleshooting) and category-specific files (for targeted debugging).

---

## Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Hierarchical namespace** | Child loggers inherit config from parent; a single `setup_logging()` call configures everything |
| **Separation by concern** | Security, performance, API, and error logs are isolated — different teams can monitor different files |
| **Rotating files** | Prevents unbounded disk growth; old logs are automatically pruned |
| **Idempotent setup** | Safe to call `setup_logging()` multiple times (tests, hot-reload) |
| **Lazy file open (`delay=True`)** | Avoids Windows file-lock issues and reduces startup overhead |
| **Third-party silencing** | Noisy libraries (uvicorn, httpx, sqlalchemy) are suppressed unless debug mode is on |
| **Log directory outside source tree** | Prevents uvicorn `--reload` from triggering restarts when logs are written |

---

## File Structure

```
your_project/
├── logs/                         # Created at runtime (gitignored)
│   ├── app.log                   # Combined log (all categories)
│   ├── api.log
│   ├── performance.log
│   ├── debug.log
│   ├── exceptions.log
│   ├── security.log
│   ├── llm.log
│   ├── integration.log
│   └── test_execution.log
├── backend/
│   ├── main.py                   # App entry point — calls setup_logging()
│   ├── config.py                 # Settings including LOG_DIR, LOG_LEVEL, etc.
│   └── common/
│       ├── middleware/
│       │   └── logging_middleware.py
│       └── utils/
│           └── logger.py         # Core logging configuration
└── .env                          # LOG_LEVEL=INFO, LOG_DIR=./logs, etc.
```

---

## Step-by-Step Implementation

### 4.1 Settings (config.py)

Add logging-related fields to your Pydantic settings class:

```python
from pathlib import Path
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Adjust for your layout

class Settings(BaseSettings):
    # ... other settings ...

    # Logging
    LOG_DIR: str = str(_PROJECT_ROOT / "logs")
    LOG_LEVEL: str = "INFO"                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_MAX_BYTES: int = 10_485_760            # 10 MiB per file before rotation
    LOG_BACKUP_COUNT: int = 5                  # Keep 5 rotated backups (.log.1 through .log.5)
    DEBUG: bool = False                        # When True, third-party loggers are not suppressed
    DB_ECHO: bool = False                      # When True, SQLAlchemy engine logs stay active

settings = Settings()
```

**Why outside `backend/`?**  
If your log directory lives inside the source tree that uvicorn watches, every log write triggers a file-change event → restart loop. Place `LOG_DIR` one level up (project root `/logs/`).

---

### 4.2 Logger Module (logger.py)

This is the core module — copy and adapt for any project.

```python
"""
Logging Configuration

Call setup_logging() once at application startup.
Use get_logger("myapp.<category>") throughout the codebase.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ─── Configuration Constants ───────────────────────────────────────────────

# Replace "myapp" with your project's namespace
_ROOT_LOGGER_NAME = "myapp"

# Category loggers: (logger_name, filename)
_LOG_CATEGORIES = [
    ("myapp.api",          "api.log"),
    ("myapp.perf",         "performance.log"),
    ("myapp.debug",        "debug.log"),
    ("myapp.exceptions",   "exceptions.log"),
    ("myapp.security",     "security.log"),
    ("myapp.llm",          "llm.log"),
    ("myapp.integration",  "integration.log"),
    ("myapp.test",         "test_execution.log"),
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


# ─── Internal Helpers ──────────────────────────────────────────────────────

def _make_rotating_handler(
    log_path: Path, max_bytes: int, backup_count: int
) -> RotatingFileHandler:
    """Create a RotatingFileHandler with delay=True (avoids Windows file-lock issues)."""
    handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    return handler


# ─── Public API ────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Initialise the logging system. Call once at application startup.
    Idempotent — safe to call multiple times; subsequent calls are no-ops.
    """
    from config import settings  # Deferred import avoids circular dependencies

    root_logger = logging.getLogger(_ROOT_LOGGER_NAME)

    # Guard: don't attach handlers twice (tests, hot-reload)
    if root_logger.handlers:
        return

    log_dir = Path(settings.LOG_DIR).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Root logger: stdout + combined app.log
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

    # Category child loggers: each gets its own file handler
    for logger_name, filename in _LOG_CATEGORIES:
        child = logging.getLogger(logger_name)
        child.propagate = True  # Records also flow to root → app.log
        child.addHandler(
            _make_rotating_handler(
                log_dir / filename,
                settings.LOG_MAX_BYTES,
                settings.LOG_BACKUP_COUNT,
            )
        )

    # Silence noisy third-party loggers in non-debug mode
    for name in _QUIET_LOGGERS:
        noisy = logging.getLogger(name)
        if not settings.DEBUG:
            noisy.setLevel(logging.WARNING)
        noisy.propagate = False

    # SQLAlchemy engine noise
    if not settings.DB_ECHO:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").propagate = False

    root_logger.info(
        "Logging initialised | level=%s | log_dir=%s",
        settings.LOG_LEVEL, str(log_dir),
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger under the project hierarchy.

    Usage:
        from common.utils.logger import get_logger
        logger = get_logger("myapp.api")
        logger.info("Request received")
    """
    return logging.getLogger(name)


# Module-level alias for backward compatibility
logger = logging.getLogger(_ROOT_LOGGER_NAME)
```

---

### 4.3 HTTP Middleware (logging_middleware.py)

Captures every request/response cycle and routes information to the appropriate category loggers.

```python
"""
HTTP Logging Middleware

Logs every request/response to multiple category loggers:
  - API log       : method, path, status code, duration, client IP
  - Performance   : duration with SLOW/VERY_SLOW/OK tags
  - Security      : 4xx responses (potential auth issues)
  - Exceptions    : unhandled exceptions with full tracebacks

Injects X-Request-ID header for cross-log correlation.
"""
import logging
import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Timing thresholds (milliseconds)
_SLOW_REQUEST_MS = 1_000
_VERY_SLOW_MS = 5_000

# Paths excluded from logging (reduces noise)
_SKIP_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
})

api_logger = logging.getLogger("myapp.api")
perf_logger = logging.getLogger("myapp.perf")
sec_logger = logging.getLogger("myapp.security")
exc_logger = logging.getLogger("myapp.exceptions")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that logs each HTTP request/response.

    Registration: add AFTER CORSMiddleware so it wraps outermost
    and captures full round-trip duration including CORS header injection.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        method = request.method
        path = request.url.path
        query = f"?{request.url.query}" if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "-")

        start = time.perf_counter()

        # Log incoming request
        api_logger.info(
            "[%s] --> %s %s%s | ip=%s",
            request_id, method, path, query, client_ip,
        )

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            exc_logger.critical(
                "[%s] UNHANDLED EXCEPTION | %s %s | duration=%.1fms\n%s",
                request_id, method, path, duration_ms,
                traceback.format_exc(),
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        status_code = response.status_code

        # Inject correlation header
        response.headers["X-Request-ID"] = request_id

        # API log (level varies by status code)
        self._log_api(request_id, method, path, status_code, duration_ms, client_ip, user_agent)

        # Performance log (tag: OK / SLOW / VERY_SLOW)
        self._log_performance(request_id, method, path, status_code, duration_ms, client_ip)

        # Security log: 4xx except 404 (potential probing)
        if 400 <= status_code < 500 and status_code != 404:
            sec_logger.warning(
                "[%s] %s %s%s -> %d | ip=%s | ua=%s",
                request_id, method, path, query, status_code, client_ip, user_agent,
            )

        return response

    @staticmethod
    def _log_api(request_id, method, path, status_code, duration_ms, client_ip, user_agent):
        msg = "[%s] <-- %s %s | status=%d | duration=%.1fms | ip=%s | ua=%s"
        args = (request_id, method, path, status_code, duration_ms, client_ip, user_agent)
        if status_code >= 500:
            api_logger.error(msg, *args)
        elif status_code >= 400:
            api_logger.warning(msg, *args)
        else:
            api_logger.info(msg, *args)

    @staticmethod
    def _log_performance(request_id, method, path, status_code, duration_ms, client_ip):
        if duration_ms >= _VERY_SLOW_MS:
            tag, level = "VERY_SLOW", logging.ERROR
        elif duration_ms >= _SLOW_REQUEST_MS:
            tag, level = "SLOW", logging.WARNING
        else:
            tag, level = "OK", logging.INFO

        perf_logger.log(
            level,
            "[%s] %s %s | status=%d | duration_ms=%.1f | ip=%s | %s",
            request_id, method, path, status_code, duration_ms, client_ip, tag,
        )
```

---

### 4.4 Application Startup (main.py)

The critical ordering: **call `setup_logging()` before importing any module that uses `get_logger()`**.

```python
"""Application Entry Point"""
from config import settings

# ⚠️ MUST be called before any other project imports
from common.utils.logger import setup_logging
setup_logging()

# Now safe to import the rest (these may call get_logger at module level)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from common.middleware.logging_middleware import LoggingMiddleware
from api.v1.router import api_router


def create_application() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

    # CORS first (registered last = wraps innermost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging middleware — outermost wrapper
    app.add_middleware(LoggingMiddleware)

    app.include_router(api_router, prefix="/api/v1")
    return app

app = create_application()
```

---

### 4.5 Using Loggers in Business Code

```python
# In any module:
from common.utils.logger import get_logger

logger = get_logger("myapp.llm")

async def call_llm(prompt: str) -> str:
    logger.info("LLM request | model=%s | prompt_len=%d", model_name, len(prompt))
    try:
        result = await client.generate(prompt)
        logger.info("LLM response | tokens=%d | latency=%.1fms", result.tokens, result.latency_ms)
        return result.text
    except Exception as e:
        logger.error("LLM call failed | error=%s", str(e), exc_info=True)
        raise
```

---

## Log File Output

### Format

```
2026-05-13 14:32:01 | INFO     | myapp.api | [abc-123] --> GET /api/v1/projects | ip=192.168.1.10
2026-05-13 14:32:01 | INFO     | myapp.api | [abc-123] <-- GET /api/v1/projects | status=200 | duration=45.2ms | ip=192.168.1.10 | ua=Mozilla/5.0
2026-05-13 14:32:01 | INFO     | myapp.perf | [abc-123] GET /api/v1/projects | status=200 | duration_ms=45.2 | ip=192.168.1.10 | OK
```

### Rotation Behavior

```
logs/
├── app.log          ← current (up to 10 MiB)
├── app.log.1        ← previous
├── app.log.2
├── app.log.3
├── app.log.4
└── app.log.5        ← oldest (auto-deleted when .6 would be created)
```

---

## Customizing for Your Project

### Replace the Namespace

Search-and-replace `myapp` (or `qastra`) with your project name:

```python
_ROOT_LOGGER_NAME = "yourproject"
_LOG_CATEGORIES = [
    ("yourproject.api", "api.log"),
    ("yourproject.perf", "performance.log"),
    # ...
]
```

### Add or Remove Categories

Add domain-specific categories relevant to your application:

```python
_LOG_CATEGORIES = [
    ("yourproject.api",       "api.log"),
    ("yourproject.perf",      "performance.log"),
    ("yourproject.exceptions","exceptions.log"),
    ("yourproject.security",  "security.log"),
    # Add your own:
    ("yourproject.payments",  "payments.log"),
    ("yourproject.scheduler", "scheduler.log"),
    ("yourproject.emails",    "emails.log"),
]
```

### Adjust Thresholds

```python
# In logging_middleware.py
_SLOW_REQUEST_MS = 2_000   # Your SLA target
_VERY_SLOW_MS = 10_000     # Alert threshold

# In config / .env
LOG_MAX_BYTES=52428800      # 50 MiB per file for high-traffic apps
LOG_BACKUP_COUNT=10         # Keep more history
LOG_LEVEL=DEBUG             # During development
```

### Suppress Additional Libraries

```python
_QUIET_LOGGERS = [
    "uvicorn.access",
    "uvicorn.error",
    "httpx",
    "httpcore",
    "boto3",          # AWS SDK
    "botocore",
    "celery",
    "redis",
    "elasticsearch",
]
```

---

## Platform Considerations (Windows)

| Issue | Solution |
|-------|----------|
| File locks prevent rotation | `delay=True` on RotatingFileHandler (opens file only on first write) |
| Path separators | Use `pathlib.Path` everywhere; never hardcode `/` |
| Uvicorn restart loops | Place `LOG_DIR` outside the watched source directory |
| PyInstaller frozen exe | Detect `getattr(sys, 'frozen', False)` and resolve paths from `sys.executable` |

---

## Production Best Practices

1. **Always use structured fields** — `key=value` format enables grep/awk/log-aggregator parsing
2. **Include request IDs** — Correlate logs across files using the `X-Request-ID` header
3. **Don't log sensitive data** — Never log passwords, tokens, or PII; mask or omit them
4. **Use appropriate levels:**
   - `DEBUG` — Developer diagnostics (disabled in production)
   - `INFO` — Normal operations (request served, job completed)
   - `WARNING` — Recoverable anomaly (slow query, retry succeeded)
   - `ERROR` — Something failed but the app continues
   - `CRITICAL` — Unhandled exception, app may need restart
5. **Monitor `performance.log`** — Alert on `VERY_SLOW` entries in production
6. **Monitor `security.log`** — Feed into SIEM for 4xx spike detection
7. **Git-ignore the logs directory** — Add `logs/` to `.gitignore`
8. **Consider log aggregation** — For multi-instance deployments, ship logs to ELK/Loki/CloudWatch via a sidecar or additional handler

---

## Environment Variables (.env)

```bash
# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
DEBUG=false
DB_ECHO=false
```

---

## Quick Start Checklist

- [ ] Copy `logger.py` into your project's utils
- [ ] Replace `_ROOT_LOGGER_NAME` and category prefixes with your project name
- [ ] Add `LOG_DIR`, `LOG_LEVEL`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT` to your settings
- [ ] Call `setup_logging()` at the top of `main.py` before other imports
- [ ] Copy `logging_middleware.py` and register it via `app.add_middleware(LoggingMiddleware)`
- [ ] Add `logs/` to `.gitignore`
- [ ] Use `get_logger("yourproject.<category>")` in all modules
- [ ] Test: start the app, hit an endpoint, verify logs appear in `logs/api.log` and `logs/app.log`
