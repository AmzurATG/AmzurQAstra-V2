"""
Global FastAPI Exception Handlers

Registers handlers for every exception type in the QAstra hierarchy so that:
  - All errors produce a consistent ErrorResponse JSON body
  - Each error type is routed to the appropriate log category
  - Full tracebacks are captured for unexpected errors

Usage (in main.py):
    from common.api.exception_handlers import register_exception_handlers
    register_exception_handlers(app)
"""
import logging
import traceback

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from common.api.responses import ErrorResponse
from common.utils.exceptions import (
    AuthenticationError,
    AuthorizationError,
    IntegrationError,
    LLMError,
    MCPError,
    NotFoundError,
    QAstraException,
    TestExecutionError,
    ValidationError as QAstraValidationError,
)

api_logger   = logging.getLogger("qastra.api")
exc_logger   = logging.getLogger("qastra.exceptions")
sec_logger   = logging.getLogger("qastra.security")
llm_logger   = logging.getLogger("qastra.llm")
int_logger   = logging.getLogger("qastra.integration")
test_logger  = logging.getLogger("qastra.test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "-")


def _json_error(
    status_code: int,
    message: str,
    error_code: str | None = None,
    details: dict | None = None,
) -> JSONResponse:
    body = ErrorResponse(message=message, error_code=error_code, details=details)
    return JSONResponse(status_code=status_code, content=body.model_dump())


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic / FastAPI request validation errors (422)."""
    rid = _request_id(request)
    errors = exc.errors()
    api_logger.warning(
        "[%s] VALIDATION_ERROR | %s %s | fields=%s",
        rid, request.method, request.url.path,
        [f"{e['loc']} — {e['msg']}" for e in errors],
    )
    return _json_error(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        details={"errors": errors},
    )


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Standard FastAPI/Starlette HTTPException."""
    rid = _request_id(request)
    msg = f"[{rid}] HTTP_{exc.status_code} | {request.method} {request.url.path} | {exc.detail}"

    if exc.status_code >= 500:
        exc_logger.error(msg)
    elif exc.status_code in (401, 403):
        sec_logger.warning(msg)
    elif exc.status_code == 404:
        api_logger.info(msg)
    else:
        api_logger.warning(msg)

    return _json_error(
        exc.status_code,
        message=str(exc.detail),
        error_code=f"HTTP_{exc.status_code}",
    )


async def _not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    rid = _request_id(request)
    api_logger.info(
        "[%s] NOT_FOUND | %s %s | %s",
        rid, request.method, request.url.path, exc.message,
    )
    return _json_error(status.HTTP_404_NOT_FOUND, exc.message, exc.error_code)


async def _authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    rid = _request_id(request)
    sec_logger.warning(
        "[%s] AUTH_FAILED | %s %s | %s",
        rid, request.method, request.url.path, exc.message,
    )
    return _json_error(status.HTTP_401_UNAUTHORIZED, exc.message, exc.error_code)


async def _authorization_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    rid = _request_id(request)
    sec_logger.warning(
        "[%s] PERMISSION_DENIED | %s %s | %s",
        rid, request.method, request.url.path, exc.message,
    )
    return _json_error(status.HTTP_403_FORBIDDEN, exc.message, exc.error_code)


async def _qastra_validation_handler(request: Request, exc: QAstraValidationError) -> JSONResponse:
    rid = _request_id(request)
    api_logger.warning(
        "[%s] DOMAIN_VALIDATION | %s %s | %s",
        rid, request.method, request.url.path, exc.message,
    )
    return _json_error(
        status.HTTP_400_BAD_REQUEST,
        exc.message,
        exc.error_code,
        exc.details if isinstance(exc.details, dict) else None,
    )


async def _integration_error_handler(request: Request, exc: IntegrationError) -> JSONResponse:
    rid = _request_id(request)
    int_logger.error(
        "[%s] INTEGRATION_ERROR | %s %s | %s",
        rid, request.method, request.url.path, exc.message,
    )
    return _json_error(status.HTTP_502_BAD_GATEWAY, exc.message, exc.error_code)


async def _llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    rid = _request_id(request)
    llm_logger.error(
        "[%s] LLM_ERROR | %s %s | %s | details=%s",
        rid, request.method, request.url.path, exc.message, exc.details,
    )
    return _json_error(status.HTTP_503_SERVICE_UNAVAILABLE, exc.message, exc.error_code)


async def _mcp_error_handler(request: Request, exc: MCPError) -> JSONResponse:
    rid = _request_id(request)
    exc_logger.error(
        "[%s] MCP_ERROR | %s %s | %s",
        rid, request.method, request.url.path, exc.message,
    )
    return _json_error(status.HTTP_502_BAD_GATEWAY, exc.message, exc.error_code)


async def _test_execution_handler(request: Request, exc: TestExecutionError) -> JSONResponse:
    rid = _request_id(request)
    test_logger.error(
        "[%s] TEST_EXECUTION_ERROR | %s %s | %s | details=%s",
        rid, request.method, request.url.path, exc.message, exc.details,
    )
    return _json_error(status.HTTP_500_INTERNAL_SERVER_ERROR, exc.message, exc.error_code)


async def _qastra_base_handler(request: Request, exc: QAstraException) -> JSONResponse:
    """Catch-all for any QAstraException subclass not matched above."""
    rid = _request_id(request)
    exc_logger.error(
        "[%s] QASTRA_EXCEPTION | %s %s | %s | code=%s",
        rid, request.method, request.url.path, exc.message, exc.error_code,
    )
    return _json_error(status.HTTP_400_BAD_REQUEST, exc.message, exc.error_code)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler — logs full traceback at CRITICAL level."""
    rid = _request_id(request)
    exc_logger.critical(
        "[%s] UNHANDLED_EXCEPTION | %s %s | %s: %s\n%s",
        rid,
        request.method,
        request.url.path,
        type(exc).__name__,
        exc,
        traceback.format_exc(),
    )
    return _json_error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred. Please try again later.",
        error_code="INTERNAL_SERVER_ERROR",
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all QAstra exception handlers to the FastAPI application.
    Call this at the end of create_application() before returning the app.

    Handler resolution order (most-specific first — FastAPI matches by MRO):
      RequestValidationError  (pydantic/fastapi built-in)
      HTTPException           (fastapi built-in)
      NotFoundError           (QAstraException subclass)
      AuthenticationError     (QAstraException subclass)
      AuthorizationError      (QAstraException subclass)
      QAstraValidationError   (QAstraException subclass)
      IntegrationError        (QAstraException subclass)
      LLMError                (QAstraException subclass)
      MCPError                (QAstraException subclass)
      TestExecutionError      (QAstraException subclass)
      QAstraException         (base — catches remaining subclasses)
      Exception               (Python root — catches everything else)
    """
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)

    # Specific QAstraException subclasses (register before the base class)
    app.add_exception_handler(NotFoundError, _not_found_handler)
    app.add_exception_handler(AuthenticationError, _authentication_handler)
    app.add_exception_handler(AuthorizationError, _authorization_handler)
    app.add_exception_handler(QAstraValidationError, _qastra_validation_handler)
    app.add_exception_handler(IntegrationError, _integration_error_handler)
    app.add_exception_handler(LLMError, _llm_error_handler)
    app.add_exception_handler(MCPError, _mcp_error_handler)
    app.add_exception_handler(TestExecutionError, _test_execution_handler)

    # Base QAstra exception (catches any unmapped subclass)
    app.add_exception_handler(QAstraException, _qastra_base_handler)

    # Absolute last resort — catches anything that escaped all other handlers
    app.add_exception_handler(Exception, _unhandled_exception_handler)
