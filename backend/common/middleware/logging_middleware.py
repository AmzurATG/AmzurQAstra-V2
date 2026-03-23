"""
HTTP Logging Middleware

Intercepts every request/response cycle to produce:
  - API log      : method, path, status code, duration, client IP, request-id
  - Performance log : same fields in a metrics-friendly format, with SLOW/FAST tag
  - Security log  : 4xx responses (potential auth/authz issues) get an extra warning
  - Exception log : unhandled exceptions that escape the route handler

A unique X-Request-ID header is injected into every response so frontend teams
and log aggregators can correlate requests across log files.
"""
import logging
import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Thresholds (milliseconds)
_SLOW_REQUEST_MS = 1_000   # Warn in performance log above this duration
_VERY_SLOW_MS    = 5_000   # Error in performance log above this duration

# Paths excluded from access logging to reduce noise
_SKIP_PATHS = frozenset({
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
})

api_logger  = logging.getLogger("qastra.api")
perf_logger = logging.getLogger("qastra.perf")
sec_logger  = logging.getLogger("qastra.security")
exc_logger  = logging.getLogger("qastra.exceptions")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that logs each HTTP request/response.

    Registration order note: add_middleware() wraps in reverse order, so register
    LoggingMiddleware AFTER CORSMiddleware so it sits outermost and captures the
    full round-trip duration including CORS header injection.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip noisy internal paths
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        method     = request.method
        path       = request.url.path
        query      = f"?{request.url.query}" if request.url.query else ""
        client_ip  = (request.client.host if request.client else "unknown")
        user_agent = request.headers.get("user-agent", "-")

        start = time.perf_counter()

        # Log the incoming request
        api_logger.info(
            "[%s] --> %s %s%s | ip=%s",
            request_id, method, path, query, client_ip,
        )

        response: Response
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            exc_logger.critical(
                "[%s] UNHANDLED EXCEPTION | %s %s | duration=%.1fms\n%s",
                request_id, method, path, duration_ms,
                traceback.format_exc(),
            )
            raise exc

        duration_ms  = round((time.perf_counter() - start) * 1000, 2)
        status_code  = response.status_code

        # Inject correlation header so clients can reference it in support requests
        response.headers["X-Request-ID"] = request_id

        # --- API log ---
        _log_api(request_id, method, path, status_code, duration_ms, client_ip, user_agent)

        # --- Performance log ---
        _log_performance(request_id, method, path, status_code, duration_ms, client_ip)

        # --- Security log: unexpected 4xx may indicate probing / auth failures ---
        if 400 <= status_code < 500 and status_code not in (404,):
            sec_logger.warning(
                "[%s] %s %s%s -> %d | ip=%s | ua=%s",
                request_id, method, path, query, status_code, client_ip, user_agent,
            )

        return response


# ---------------------------------------------------------------------------
# Helpers (kept small so dispatch() stays readable)
# ---------------------------------------------------------------------------

def _log_api(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str,
    user_agent: str,
) -> None:
    msg = "[%s] <-- %s %s | status=%d | duration=%.1fms | ip=%s | ua=%s"
    args = (request_id, method, path, status_code, duration_ms, client_ip, user_agent)

    if status_code >= 500:
        api_logger.error(msg, *args)
    elif status_code >= 400:
        api_logger.warning(msg, *args)
    else:
        api_logger.info(msg, *args)


def _log_performance(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    client_ip: str,
) -> None:
    if duration_ms >= _VERY_SLOW_MS:
        tag   = "VERY_SLOW"
        level = logging.ERROR
    elif duration_ms >= _SLOW_REQUEST_MS:
        tag   = "SLOW"
        level = logging.WARNING
    else:
        tag   = "OK"
        level = logging.INFO

    perf_logger.log(
        level,
        "[%s] %s %s | status=%d | duration_ms=%.1f | ip=%s | %s",
        request_id, method, path, status_code, duration_ms, client_ip, tag,
    )
