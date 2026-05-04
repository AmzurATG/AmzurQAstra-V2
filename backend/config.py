"""
Application settings loaded from environment / backend/.env.

Frozen-aware: when running as a PyInstaller exe, paths resolve
relative to sys.executable (where the .env and runtime data live)
instead of __file__ (which points to the temp _MEIPASS folder).
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any, List, Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Code/data root: inside _MEIPASS when frozen, backend/ dir in dev.
_BACKEND_DIR = Path(__file__).resolve().parent


def _resolve_env_file() -> str:
    """
    Resolve .env location:
    - Frozen exe: .env sits next to QAstra.exe (sys.executable's parent)
    - Dev mode:   .env sits inside backend/
    """
    if getattr(sys, 'frozen', False):
        return str(Path(sys.executable).parent / ".env")
    return str(_BACKEND_DIR / ".env")


def _resolve_app_root() -> Path:
    """
    Resolve the application root directory for runtime data
    (logs, screenshots, storage, uploads).
    - Frozen exe: the folder containing QAstra.exe
    - Dev mode:   the project root (parent of backend/)
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return _BACKEND_DIR.parent


_APP_ROOT = _resolve_app_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "QAstra"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: Any) -> Any:
        if v is None or v == "":
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        if isinstance(v, list):
            return v
        s = str(v).strip()
        if s.startswith("["):
            return json.loads(s)
        return [x.strip() for x in s.split(",") if x.strip()]

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: Optional[str] = None

    # Security
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "litellm"
    DEFAULT_LLM_MODEL: str = "gpt-4o"

    LITELLM_API_KEY: Optional[str] = None
    LITELLM_API_BASE: Optional[str] = None
    LITELLM_MODEL: str = "gpt-4o"
    # Comma-separated list of proxy model ids to try if the primary model fails
    LITELLM_FALLBACK_MODELS: Optional[str] = None

    # Browser agent (browser-use)
    # LLM backend: "litellm" uses ChatLiteLLM + LITELLM_* (default, same proxy as the app).
    # "google" uses ChatGoogle + GEMINI_API_KEY (direct Gemini, no proxy).
    BROWSER_USE_LLM_BACKEND: str = "litellm"
    # If unset, browser uses LITELLM_MODEL (litellm) or gemini-2.0-flash (google).
    BROWSER_USE_LLM_MODEL: Optional[str] = None
    BROWSER_USE_LLM_TEMPERATURE: float = 0.15
    GEMINI_API_KEY: Optional[str] = None  # only when BROWSER_USE_LLM_BACKEND=google
    BROWSER_USE_DEFAULT_EXTENSIONS: bool = True
    # Comma-separated extra Chrome flags appended after defaults (see chrome_automation_args).
    BROWSER_CHROME_EXTRA_ARGS: Optional[str] = None
    # Outside backend/ to prevent uvicorn --reload restarts when screenshots are written.
    SCREENSHOTS_DIR: str = str(_APP_ROOT / "screenshots")

    # MCP (optional)
    MCP_SERVER_URL: str = "http://localhost:3001"

    # Integrations
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Outbound email (SMTP) — optional; required to email gap / test-recommendation PDFs
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 30
    EMAIL_FROM_ADDRESS: Optional[str] = None
    EMAIL_FROM_NAME: Optional[str] = None

    # Storage
    STORAGE_TYPE: str = "local"
    STORAGE_LOCAL_PATH: str = str(_APP_ROOT / "storage")
    STORAGE_S3_BUCKET: Optional[str] = None
    STORAGE_S3_REGION: Optional[str] = None
    STORAGE_S3_ACCESS_KEY: Optional[str] = None
    STORAGE_S3_SECRET_KEY: Optional[str] = None
    STORAGE_S3_ENDPOINT_URL: Optional[str] = None
    STORAGE_S3_PREFIX: Optional[str] = None
    STORAGE_SUPABASE_URL: Optional[str] = None
    STORAGE_SUPABASE_KEY: Optional[str] = None
    STORAGE_SUPABASE_BUCKET: Optional[str] = None
    STORAGE_SUPABASE_PREFIX: Optional[str] = None

    UPLOAD_DIR: str = str(_APP_ROOT / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 50
    # Requirement document uploads (5 MiB); enforced in RequirementService
    REQUIREMENT_UPLOAD_MAX_BYTES: int = 5 * 1024 * 1024

    # Test recommendations: domain playbook (YAML) + LLM reads BRD/story intent to pick domain
    # When True (default), LLM classifies domain first; keyword scores are diagnostics / fallback only.
    TEST_RECOMMENDATION_USE_LLM_FOR_DOMAIN: bool = True
    # When USE_LLM_FOR_DOMAIN is False: keyword-first, then LLM if confidence below threshold
    TEST_RECOMMENDATION_LLM_FALLBACK_ENABLED: bool = True
    TEST_RECOMMENDATION_DOMAIN_CONFIDENCE_THRESHOLD: float = 0.6
    TEST_RECOMMENDATION_LLM_MAX_CORPUS_CHARS: int = 48_000
    # Second LLM call: narrative + per-playbook-row guidance (requires gap analysis snapshot)
    TEST_RECOMMENDATION_DETAIL_LLM_ENABLED: bool = True

    # PDF generation (fpdf2)
    PDF_FONT_PATH: Optional[str] = None

    # Default Admin Account
    ADMIN_EMAIL: str = "admin@qastra.dev"
    ADMIN_PASSWORD: str = "admin123"

    # Logging (outside backend/ to prevent uvicorn restart)
    LOG_DIR: str = str(_APP_ROOT / "logs")
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10_485_760
    LOG_BACKUP_COUNT: int = 5

    @field_validator(
        "LOG_DIR", "SCREENSHOTS_DIR", "STORAGE_LOCAL_PATH", "UPLOAD_DIR",
        mode="after",
    )
    @classmethod
    def _resolve_runtime_dir(cls, v: str) -> str:
        """
        Ensure runtime data directories are absolute.
        Relative paths in .env are resolved against _BACKEND_DIR (where .env
        lives), so that '../logs' correctly points to the project root's logs/.
        In frozen mode, relative paths resolve against the exe directory.
        """
        p = Path(v)
        if not p.is_absolute():
            if getattr(sys, 'frozen', False):
                p = Path(sys.executable).parent / p
            else:
                p = _BACKEND_DIR / p
        return str(p.resolve())


settings = Settings()
