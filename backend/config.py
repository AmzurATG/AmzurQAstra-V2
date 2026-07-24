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
    DB_SCHEMA: str
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
    REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_NONCE: Optional[str] = None  # Stable nonce for JWT; if unset, tokens invalidate on restart

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
    # Comma-separated fallbacks when primary is rate-limited / unavailable.
    # Falls back to LITELLM_FALLBACK_MODELS, then gpt-4o.
    BROWSER_USE_FALLBACK_MODELS: Optional[str] = "gpt-4o"
    GEMINI_API_KEY: Optional[str] = None  # only when BROWSER_USE_LLM_BACKEND=google
    BROWSER_USE_DEFAULT_EXTENSIONS: bool = True

    # LangGraph orchestrated run-all (local browsers).
    # Default kept modest so parallel vision calls don't exhaust the shared LLM
    # proxy / hit rate limits (accuracy over raw speed). Raise on RAM+quota-rich setups.
    ORCHESTRATION_LANE_COUNT: int = 6
    ORCHESTRATION_MAX_LANE_COUNT: int = 12
    ORCHESTRATION_CHROME_PROCESSES: int = 2
    ORCHESTRATION_CONTEXTS_PER_CHROME: int = 3
    ORCHESTRATION_MIN_FREE_RAM_MB: int = 800
    ORCHESTRATION_PER_LANE_RAM_MB: int = 320
    # Never auto-bump above requested lane count (scale down only under RAM pressure).
    ORCHESTRATION_LANE_SCALE_UP: bool = False
    ORCHESTRATION_REASONING_MODEL: str = "gpt-4o"
    ORCHESTRATION_VISION_RETRY_MODEL: str = ""
    ORCHESTRATION_PLANNER_CHUNK_TOKENS: int = 12000
    ORCHESTRATION_MAX_PLANNERS: int = 4
    # Tuned for ~200 cases / hour on 6 lanes (~108s avg/case) with shared login.
    TEST_CASE_MAX_AGENT_STEPS: int = 28

    # ── Accuracy + supervisor stack ──────────────────────────────────────────
    ACCURACY_REQUIRE_SCREENSHOTS: bool = True
    ACCURACY_REQUIRE_PARSED_VERDICT: bool = True
    ACCURACY_LANE_COUNT_CAP: int = 0
    SUBGROUP_MAX_CASES_MUTATING: int = 10
    SUBGROUP_MAX_CASES_READONLY: int = 16
    UI_VALIDATION_ENABLED: bool = True
    UI_VALIDATION_MODEL: str = ""
    UI_VALIDATION_CONFIDENCE: float = 0.75
    # Sample fewer passing cases for vision re-check — keeps throughput up.
    UI_VALIDATION_PASS_SAMPLE_RATE: float = 0.08
    PROMPT_UI_VALIDATION_VERSION: str = "v1"
    UI_CONSISTENCY_ENABLED: bool = True
    UI_CONSISTENCY_EVERY_N: int = 10
    SUPERVISOR_ENABLED: bool = True
    RECON_ENABLED: bool = True
    RECON_TIMEOUT_S: int = 60
    LANE_HEARTBEAT_S: float = 90.0
    # Only treat as "slow" after long-case budget (10 min) — complex cases need room.
    SLOW_CASE_MS: int = 600_000
    MAX_CASE_REASSIGNS: int = 2
    LANE_QUARANTINE_FAILURES: int = 3
    # Ignore short quiet periods; only stale-reassign after this much elapsed.
    WATCHDOG_MIN_ELAPSED_BEFORE_STALE_S: float = 90.0

    # Screenshot evidence agent — curb agent-frame spam (e.g. "120 screenshots").
    SCREENSHOT_EVIDENCE_MAX_PASS: int = 6
    SCREENSHOT_EVIDENCE_MAX_FAIL: int = 8
    SCREENSHOT_RAW_CAP: int = 24
    # Capture every Nth agent micro-step (1 = all, within RAW_CAP). 2 cuts I/O ~50%.
    SCREENSHOT_CAPTURE_EVERY_N: int = 2

    # ── LLM resilience gate (shared across ALL browser lanes) ────────────────
    # Match lane count so 6 browsers are not stalled behind a 4-call gate.
    LLM_MAX_INFLIGHT: int = 6
    LLM_RATE_LIMIT_RPM: int = 180
    LLM_CALL_TIMEOUT_S: float = 75.0
    LLM_CB_FAILURE_THRESHOLD: int = 6
    LLM_CB_DEGRADE_THRESHOLD: int = 3
    LLM_CB_COOLDOWN_S: float = 30.0
    LLM_CB_HALFOPEN_PROBES: int = 2
    LLM_CB_BUDGET_COOLDOWN_S: float = 900.0
    LLM_RETRY_MAX: int = 2
    LLM_RETRY_BASE_S: float = 2.0
    # Adaptive case budgets: typical ~4m, complex ~10m, reassign up to ~15m.
    TEST_CASE_WALLCLOCK_TIMEOUT_S: int = 240
    TEST_CASE_WALLCLOCK_LONG_S: int = 600
    TEST_CASE_WALLCLOCK_MAX_S: int = 900
    TEST_CASE_LONG_STEP_THRESHOLD: int = 6
    # When circuit OPEN, governor waits then pauses dispatch (graceful degradation).
    RUN_GOVERNOR_ENABLED: bool = True

    # ── Prompt versioning ────────────────────────────────────────────────────
    PROMPT_TEST_EXECUTION_VERSION: str = "v3"
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


# ---------------------------------------------------------------------------
# Enforce .env file existence — no fallback to env vars or defaults for
# required fields. Every deployment MUST have a .env alongside the app.
# ---------------------------------------------------------------------------
_env_path = Path(_resolve_env_file())
if not _env_path.is_file():
    raise FileNotFoundError(
        f"Required .env file not found at: {_env_path}\n"
        "Copy .env.example to .env and configure it before starting the application."
    )

settings = Settings()
