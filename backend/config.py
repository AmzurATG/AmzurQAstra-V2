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
    GEMINI_API_KEY: Optional[str] = None  # only when BROWSER_USE_LLM_BACKEND=google
    BROWSER_USE_DEFAULT_EXTENSIONS: bool = True
    # False = visible Chrome window (default for integrity check / UI discovery).
    BROWSER_USE_HEADLESS: bool = False
    # Comma-separated extra Chrome flags appended after defaults (see chrome_automation_args).
    BROWSER_CHROME_EXTRA_ARGS: Optional[str] = None
    # Outside backend/ to prevent uvicorn --reload restarts when screenshots are written.
    SCREENSHOTS_DIR: str = str(_APP_ROOT / "screenshots")

    # Browser engine selection
    # "chrome" (default) — local Chrome via browser-use.
    # "steel"            — Steel.dev cloud browser; browser-use connects via CDP websocket.
    BROWSER_ENGINE: str = "chrome"
    STEEL_API_KEY: Optional[str] = None
    STEEL_BASE_URL: str = "https://api.steel.dev"

    # ── Execution performance tuning ──────────────────────────────────────
    # Default strategy when a run request does not specify one.
    #   "sequential"      — one isolated browser per case, run one-by-one (slow, safe)
    #   "grouped_parallel"— AI groups cases into lanes and runs lanes in parallel (fast)
    #   "playwright"      — deterministic Playwright, no per-step LLM (fastest)
    DEFAULT_EXECUTION_STRATEGY: str = "grouped_parallel"
    # Max browser sessions open at once across all lanes in grouped_parallel.
    # IMPORTANT: cannot exceed your Steel plan's concurrent-session quota or Steel
    # rejects the extra sessions and the run errors out. Steel concurrent limits:
    #   Hobby/FREE = 5  | Starter($29) = 10 | Developer($99) = 20 | Pro($499) = 100
    # Free tier = 5 concurrent sessions total; using 4 leaves a 1-session margin so a
    # lane opening a new group's session while the previous one is still releasing
    # doesn't momentarily exceed the quota (→ 429). Raise to 16 on Steel Premium /
    # Developer+ when demoing 200–6000 cases (set MAX_CONCURRENT_BROWSERS=16 in .env).
    MAX_CONCURRENT_BROWSERS: int = 4
    # Planner batching: max test cases sent to the grouping LLM in a single call.
    # Sending hundreds of cases at once overflows the model's OUTPUT token limit,
    # so later cases silently fall back to one-by-one. Batching keeps each call
    # bounded and lets the planner scale to thousands of cases.
    PLANNER_BATCH_SIZE: int = 20
    # Max planner LLM calls to run concurrently when batching (6000 cases = many batches).
    PLANNER_MAX_CONCURRENCY: int = 8
    # Per-call timeout (seconds) for planner LLM calls. A flaky/slow proxy call fails
    # fast and retries instead of blocking for minutes and falling back to no-merging.
    PLANNER_LLM_TIMEOUT: float = 90.0
    # Below this many cases, skip the LLM planner entirely: nothing meaningful to
    # merge, and planning costs more than it saves. Cases run directly (each isolated,
    # still parallel across lanes, still per-step screenshots + detailed steps).
    GROUPING_MIN_CASES: int = 6
    # Cap cases per SHARED group. Large groups become one monster agent with a huge
    # step budget and ever-growing context (slow + unreliable). Smaller groups also
    # spread better across lanes. The planner is told this; the value bounds it.
    MAX_CASES_PER_SHARED_GROUP: int = 8

    # ── Shared-session execution mode ─────────────────────────────────────
    # "segmented" (default) — run ONE merged step at a time on a kept-alive browser
    #   session (Agent.add_new_task), capturing a ground-truth screenshot per step.
    #   Fixes per-step screenshot/log mapping AND bounds per-call context → faster.
    # "monolithic" — legacy: one agent.run over the whole merged script (fallback if
    #   the segmented path misbehaves on your environment).
    SHARED_EXECUTION_MODE: str = "segmented"
    # Per-merged-step agent budget in segmented mode (small = fast, focused).
    SEGMENT_MAX_STEPS: int = 8
    # Login/auth steps need a few more actions (2FA, redirects).
    SEGMENT_LOGIN_MAX_STEPS: int = 12
    # Screenshot capture policy for segmented runs:
    #   "per_step"   (default) — one ground-truth PNG per merged/test step (fast, relevant)
    #   "per_action" — PNG after every browser-use action (debug / max evidence; slow + disk-heavy)
    SCREENSHOT_CAPTURE_MODE: str = "per_step"
    # Keep only lite summaries in RunProgressManager during large runs (full detail via
    # GET .../results/{id}). Cuts RAM for 200–6000 case demos.
    LIVE_PROGRESS_STORE_LITE: bool = True

    # ── Plan caching ──────────────────────────────────────────────────────
    # Reuse a previously-built grouping plan when the exact same set of test cases
    # (ids + step contents + app_url) is run again — skips the multi-minute planner.
    PLAN_CACHE_ENABLED: bool = True
    PLAN_CACHE_DIR: str = str(_APP_ROOT / "storage" / "plan_cache")
    # Send a screenshot to the LLM on every agent step.
    # KEEP TRUE for JS-heavy SPAs: without vision the agent can't navigate, burns
    # its entire step budget flailing, and fails — slower AND broken. Only set
    # False for simple, DOM-stable apps you've verified work without screenshots.
    BROWSER_USE_VISION: bool = True
    # Hard cap on agent reasoning steps per case/group. 80 is a runaway ceiling,
    # but too low (≈20) starves the agent before it emits its final VERDICT_JSON
    # → "Could not parse agent output". 40 leaves headroom while still bounding cost.
    BROWSER_USE_MAX_STEPS: int = 40

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
