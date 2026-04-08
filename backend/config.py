"""
Application settings loaded from environment / backend/.env.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
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
    # Outside backend/ to prevent uvicorn --reload restarts when screenshots are written.
    SCREENSHOTS_DIR: str = str(_BACKEND_DIR.parent / "screenshots")

    # MCP (optional)
    MCP_SERVER_URL: str = "http://localhost:3001"

    # Integrations
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Storage
    STORAGE_TYPE: str = "local"
    STORAGE_LOCAL_PATH: str = "../storage"
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

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Logging (outside backend/ to prevent uvicorn restart)
    LOG_DIR: str = str(_BACKEND_DIR.parent / "logs")
    LOG_LEVEL: str = "INFO"
    LOG_MAX_BYTES: int = 10_485_760
    LOG_BACKUP_COUNT: int = 5


settings = Settings()
