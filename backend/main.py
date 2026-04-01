"""
QAstra - AI-Powered QA Automation Platform
Main FastAPI Application Entry Point
"""
# Windows: browser-use launches Chrome via asyncio.create_subprocess_exec. The selector event loop
# does not implement subprocess transport — use the Proactor policy (must run before the loop exists).
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from config import settings

# Initialise logging before any other QAstra import so that all modules that
# call get_logger() at import time already have handlers attached.
from common.utils.logger import setup_logging
setup_logging()

from api.v1.router import api_router
from common.api.exception_handlers import register_exception_handlers
from common.db.database import engine
from common.db.base import Base
from common.middleware.logging_middleware import LoggingMiddleware


_startup_logger = logging.getLogger("qastra")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    _startup_logger.info("QAstra starting up | version=%s | env=%s", settings.APP_VERSION, settings.ENVIRONMENT)

    # Tables are managed by Alembic migrations (alembic upgrade head).
    # Base.metadata.create_all is no longer called here.

    # Ensure screenshots directory exists
    screenshots_dir = Path(settings.SCREENSHOTS_DIR)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    _startup_logger.info("QAstra startup complete")
    yield

    # Shutdown
    _startup_logger.info("QAstra shutting down")
    await engine.dispose()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered QA Automation Platform",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        redirect_slashes=False,  # Prevent 307 redirects for trailing slashes
    )

    # CORS middleware (registered first — LoggingMiddleware wraps outside it)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging middleware — outermost wrapper, captures full round-trip duration
    app.add_middleware(LoggingMiddleware)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Mount static files for screenshots
    screenshots_path = Path(settings.SCREENSHOTS_DIR)
    screenshots_path.mkdir(parents=True, exist_ok=True)
    app.mount("/screenshots", StaticFiles(directory=str(screenshots_path)), name="screenshots")

    # Register global exception handlers (must be last so all routes are already registered)
    register_exception_handlers(app)

    return app


app = create_application()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
