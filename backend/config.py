"""
QAstra Configuration Settings
"""
from functools import lru_cache
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # App
    APP_NAME: str = "QAstra"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-32-byte-encryption-key-here"  # Must be 32 bytes for Fernet
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    
    # Logging — files are written outside backend/ so uvicorn --reload never triggers on log writes
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "../logs"          # Resolves to QAstra/logs/ relative to backend/ CWD
    LOG_MAX_BYTES: int = 10_485_760   # 10 MB per file before rotation
    LOG_BACKUP_COUNT: int = 5         # Number of rotated copies to keep per log file
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/qastra"
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "litellm"  # openai, anthropic, or litellm
    DEFAULT_LLM_MODEL: str = "gpt-4"
    
    # LiteLLM - Unified LLM Proxy
    LITELLM_API_KEY: Optional[str] = None
    LITELLM_API_BASE: Optional[str] = None  # e.g., http://localhost:4000 for LiteLLM proxy
    LITELLM_MODEL: str = "gpt-4"  # Model format: provider/model or just model-name
    
    # Browser: 'playwright' (local Chromium) or 'steel' (Playwright via Steel CDP).
    # Default steel when using STEEL_API_KEY; set BROWSER_ENGINE=playwright for local-only.
    BROWSER_ENGINE: str = "steel"
    STEEL_API_KEY: Optional[str] = None
    # If True, BROWSER_ENGINE=playwright still uses Steel when STEEL_API_KEY is set (hybrid).
    STEEL_USE_WITH_PLAYWRIGHT: bool = True
    # Steel Method 2: create session via steel-sdk (proxy, CAPTCHA, explicit release).
    STEEL_INTELLIGENT_SESSIONS: bool = True
    STEEL_SOLVE_CAPTCHA: bool = True
    STEEL_USE_PROXY: bool = True
    # Passed to Steel sessions.create(api_timeout=...) — milliseconds.
    STEEL_SESSION_API_TIMEOUT_MS: int = 30_000
    # Playwright timeouts (ms) and navigation resilience
    BROWSER_DEFAULT_TIMEOUT_MS: int = 30_000
    BROWSER_NAVIGATION_TIMEOUT_MS: int = 45_000
    BROWSER_NAVIGATION_RETRIES: int = 3
    BROWSER_NAVIGATION_RETRY_BACKOFF_MS: int = 2_000
    # domcontentloaded | load | networkidle
    BROWSER_NAVIGATION_WAIT_UNTIL: str = "domcontentloaded"

    # File Storage (Legacy - kept for backward compatibility)
    UPLOAD_DIR: str = "./uploads"
    # Screenshots stored outside backend to avoid uvicorn --reload triggers
    SCREENSHOTS_DIR: str = "../screenshots"
    MAX_UPLOAD_SIZE_MB: int = 50
    
    # Document Storage Configuration
    # Type: 'local', 's3', or 'supabase'
    STORAGE_TYPE: str = "local"
    
    # Local Storage - Path should be outside backend folder to prevent uvicorn restart
    # Default: ../storage (relative to backend folder, resolves to QAstra/storage/)
    STORAGE_LOCAL_PATH: str = "../storage"
    
    # AWS S3 Storage
    STORAGE_S3_BUCKET: Optional[str] = None
    STORAGE_S3_REGION: str = "us-east-1"
    STORAGE_S3_ACCESS_KEY: Optional[str] = None
    STORAGE_S3_SECRET_KEY: Optional[str] = None
    STORAGE_S3_ENDPOINT_URL: Optional[str] = None  # For S3-compatible services (MinIO, etc.)
    STORAGE_S3_PREFIX: str = ""  # Optional prefix for all files
    
    # Supabase Storage
    STORAGE_SUPABASE_URL: Optional[str] = None
    STORAGE_SUPABASE_KEY: Optional[str] = None
    STORAGE_SUPABASE_BUCKET: Optional[str] = None
    STORAGE_SUPABASE_PREFIX: str = ""
    
    # Jira Integration
    JIRA_BASE_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    
    # Azure DevOps Integration
    AZURE_DEVOPS_ORG_URL: Optional[str] = None
    AZURE_DEVOPS_PAT: Optional[str] = None
    
    # Slack Integration
    SLACK_WEBHOOK_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
