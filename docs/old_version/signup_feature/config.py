import os
import sys
import logging
import logging.handlers
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ===== UNICODE-SAFE LOGGING UTILITIES =====

class Utf8StreamHandler(logging.StreamHandler):
    """
    Custom StreamHandler that properly handles Unicode/emoji characters on Windows.
    Uses UTF-8 encoding with 'replace' error handling to prevent UnicodeEncodeError.
    """
    def __init__(self, stream=None):
        super().__init__(stream)
        # Force UTF-8 encoding with error handling for Windows compatibility
        if hasattr(self.stream, 'reconfigure'):
            try:
                # Python 3.7+ allows reconfiguring the stream encoding
                self.stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    
    def emit(self, record):
        """
        Emit a record with safe Unicode handling.
        Replaces problematic characters instead of crashing.
        """
        try:
            msg = self.format(record)
            stream = self.stream
            # Ensure message is properly encoded
            if hasattr(stream, 'buffer'):
                # Write to buffer with UTF-8 encoding
                stream.buffer.write((msg + self.terminator).encode('utf-8', errors='replace'))
                stream.buffer.flush()
            else:
                # Fallback to regular write with error handling
                try:
                    stream.write(msg + self.terminator)
                except UnicodeEncodeError:
                    # If encoding fails, replace problematic characters
                    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                    stream.write(safe_msg + self.terminator)
                self.flush()
        except Exception:
            self.handleError(record)

def safe_log_message(message: str) -> str:
    """
    Convert emoji and special Unicode characters to ASCII-safe alternatives.
    Fallback for when UTF-8 encoding is not available.
    
    Args:
        message: Log message that may contain emojis
        
    Returns:
        ASCII-safe version of the message
    """
    emoji_map = {
        '📤': '[OUT]',
        '📥': '[IN]',
        '🔍': '[SEARCH]',
        '✅': '[OK]',
        '❌': '[FAIL]',
        '⚠️': '[WARN]',
        '🚀': '[START]',
        '🛑': '[STOP]',
        '⏱️': '[TIME]',
        '🎉': '[SUCCESS]',
        '📊': '[DATA]',
        '🔐': '[AUTH]',
        '🔒': '[LOCKED]',
        '🔑': '[KEY]',
        '✓': '[CHECK]',
        '🔧': '[CONFIG]',
        'ℹ️': '[INFO]',
        '🌐': '[WEB]',
        '📦': '[PACKAGE]',
        '🏁': '[FLAG]',
        '⏱': '[TIME]',  # Alternative time emoji
    }
    
    result = message
    for emoji, replacement in emoji_map.items():
        result = result.replace(emoji, replacement)
    
    # Remove any remaining non-ASCII characters
    return result.encode('ascii', errors='replace').decode('ascii')


def reconfigure_logging_for_subprocess():
    """
    Reconfigure logging for uvicorn subprocess/worker processes.
    This ensures that spawned processes also use UTF-8 safe logging.
    Called automatically when setup_logging detects it's running in a subprocess.
    """
    # Force reconfigure stdout and stderr to UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    # Remove all existing handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add UTF-8 safe console handler
    console_handler = Utf8StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(SIMPLE_LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE")

# Email configuration for OTP
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

# OTP configuration
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", 5))  # OTP expires after 10 minutes

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-key-do-not-use-in-production")

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Social login configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:3000/auth/callback")

# Base directories
BASE_DIR = Path(__file__).resolve().parent

# Upload directories
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SDLC_DOCS_DIR = os.path.join(UPLOAD_DIR, "sdlc_docs")
TEST_RESULTS_DIR = os.path.join(UPLOAD_DIR, "test_results")

# Ensure these directories exist
for directory in [UPLOAD_DIR, SDLC_DOCS_DIR, TEST_RESULTS_DIR]:
    os.makedirs(directory, exist_ok=True)

# ===== COMPREHENSIVE LOGGING CONFIGURATION =====

# Logging environment variables with defaults
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", os.path.abspath(os.path.join(BASE_DIR, "..", "logs")))  # logs folder outside backend
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB default
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
ENABLE_CONSOLE_LOGGING = os.getenv("ENABLE_CONSOLE_LOGGING", "true").lower() == "true"
ENABLE_PERFORMANCE_LOGGING = os.getenv("ENABLE_PERFORMANCE_LOGGING", "true").lower() == "true"

# SQL query logging configuration
ENABLE_SQL_LOGGING = os.getenv("ENABLE_SQL_LOGGING", "true").lower() == "true"
SQL_LOG_LEVEL = os.getenv("SQL_LOG_LEVEL", "INFO").upper()
LOG_SQL_QUERIES = os.getenv("LOG_SQL_QUERIES", "true").lower() == "true"
LOG_SQL_RESULTS = os.getenv("LOG_SQL_RESULTS", "false").lower() == "true"
ENABLE_REQUEST_LOGGING = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"

# Log format configurations
DETAILED_LOG_FORMAT = "%(asctime)s | %(name)-20s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s"
SIMPLE_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
PERFORMANCE_LOG_FORMAT = "%(asctime)s | PERF | %(name)-15s | %(message)s"
REQUEST_LOG_FORMAT = "%(asctime)s | REQ | %(message)s"
SQL_LOG_FORMAT = "%(asctime)s | SQL | %(name)-15s | %(message)s"

# Global logging state
_logging_initialized = False

def setup_logging():
    """
    Configure comprehensive logging for the AmzurQAstra application.
    
    Creates separate log files for:
    - app.log: Main application logs
    - performance.log: Performance metrics and timing
    - error.log: Errors and exceptions only  
    - requests.log: HTTP request/response logs
    - debug.log: Debug information
    - uvicorn.log: Uvicorn server logs
    - uvicorn_access.log: Uvicorn access logs
    """
    global _logging_initialized
    if _logging_initialized:
        return get_logger("config")
    
    # ===== FORCE UTF-8 ENCODING FOR STDOUT/STDERR =====
    # This is critical for Windows compatibility with emoji characters
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    
    # Create logs directory outside backend folder
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # ===== CLEAR ALL EXISTING HANDLERS =====
    # Remove any handlers that may have been added before our configuration
    # This is especially important for uvicorn subprocesses
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Also clear handlers from common third-party loggers
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error', 'fastapi']:
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # ===== ROOT LOGGER CONFIGURATION =====
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Console handler (if enabled) - Use UTF-8 safe handler
    if ENABLE_CONSOLE_LOGGING:
        console_handler = Utf8StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(SIMPLE_LOG_FORMAT)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Main application log file handler
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'  # Force UTF-8 encoding for file
    )
    app_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    app_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    app_handler.setFormatter(app_formatter)
    root_logger.addHandler(app_handler)
    
    # ===== PERFORMANCE LOGGER =====
    performance_logger = logging.getLogger("performance")
    performance_logger.setLevel(logging.INFO)
    performance_logger.handlers.clear()
    performance_logger.propagate = False  # Don't propagate to root logger
    
    performance_handler = logging.handlers.RotatingFileHandler(
        log_dir / "performance.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    performance_formatter = logging.Formatter(PERFORMANCE_LOG_FORMAT)
    performance_handler.setFormatter(performance_formatter)
    performance_logger.addHandler(performance_handler)
    
    # ===== ERROR LOGGER =====
    error_logger = logging.getLogger("error")
    error_logger.setLevel(logging.ERROR)
    error_logger.handlers.clear()
    error_logger.propagate = False
    
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    error_handler.setFormatter(error_formatter)
    error_logger.addHandler(error_handler)
    
    # ===== REQUEST LOGGER =====
    request_logger = logging.getLogger("requests")
    request_logger.setLevel(logging.INFO)
    request_logger.handlers.clear()
    request_logger.propagate = False
    
    request_handler = logging.handlers.RotatingFileHandler(
        log_dir / "requests.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    request_formatter = logging.Formatter(REQUEST_LOG_FORMAT)
    request_handler.setFormatter(request_formatter)
    request_logger.addHandler(request_handler)
    
    # ===== DEBUG LOGGER =====
    debug_logger = logging.getLogger("debug")
    debug_logger.setLevel(logging.DEBUG)
    debug_logger.handlers.clear()
    debug_logger.propagate = False
    
    debug_handler = logging.handlers.RotatingFileHandler(
        log_dir / "debug.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    debug_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    debug_handler.setFormatter(debug_formatter)
    debug_logger.addHandler(debug_handler)
    
    # ===== BIC LOGGER (Build Integrity Check - backend/logs/bic.log) =====
    # Dedicated log file for BIC debugging. QA can send bic.log for fast troubleshooting.
    bic_log_dir = Path(BASE_DIR) / "logs"
    bic_log_dir.mkdir(exist_ok=True, parents=True)
    bic_logger = logging.getLogger("bic")
    bic_logger.setLevel(logging.DEBUG)
    bic_logger.handlers.clear()
    bic_logger.propagate = True  # Also propagate to root for app.log
    bic_handler = logging.handlers.RotatingFileHandler(
        bic_log_dir / "bic.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    bic_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    bic_handler.setFormatter(bic_formatter)
    bic_logger.addHandler(bic_handler)
    
    # ===== SQL LOGGER =====
    sql_logger = logging.getLogger("sql")
    sql_logger.setLevel(getattr(logging, SQL_LOG_LEVEL, logging.INFO))
    sql_logger.handlers.clear()
    sql_logger.propagate = False
    
    sql_handler = logging.handlers.RotatingFileHandler(
        log_dir / "qastra_sql.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    sql_formatter = logging.Formatter(SQL_LOG_FORMAT)
    sql_handler.setFormatter(sql_formatter)
    sql_logger.addHandler(sql_handler)
    
    # Configure SQLAlchemy logging for database queries
    if ENABLE_SQL_LOGGING:
        # Log SQL queries
        sqlalchemy_engine_logger = logging.getLogger("sqlalchemy.engine")
        sqlalchemy_engine_logger.setLevel(getattr(logging, SQL_LOG_LEVEL, logging.INFO))
        sqlalchemy_engine_logger.handlers.clear()
        sqlalchemy_engine_logger.addHandler(sql_handler)
        sqlalchemy_engine_logger.propagate = False
        
        # Log connection pool info
        sqlalchemy_pool_logger = logging.getLogger("sqlalchemy.pool")
        sqlalchemy_pool_logger.setLevel(logging.WARNING)  # Usually less verbose
        sqlalchemy_pool_logger.handlers.clear()
        sqlalchemy_pool_logger.addHandler(sql_handler)
        sqlalchemy_pool_logger.propagate = False
        
        # Log SQL results if enabled (can be very verbose)
        if LOG_SQL_RESULTS:
            sqlalchemy_result_logger = logging.getLogger("sqlalchemy.engine.result")
            sqlalchemy_result_logger.setLevel(getattr(logging, SQL_LOG_LEVEL, logging.INFO))
            sqlalchemy_result_logger.handlers.clear()
            sqlalchemy_result_logger.addHandler(sql_handler)
            sqlalchemy_result_logger.propagate = False
    
    # ===== UVICORN LOGGERS =====
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = False
    uvicorn_logger.setLevel(logging.INFO)
    
    # Add UTF-8 console handler for uvicorn
    uvicorn_console = Utf8StreamHandler(sys.stdout)
    uvicorn_console.setLevel(logging.INFO)
    uvicorn_console.setFormatter(logging.Formatter(SIMPLE_LOG_FORMAT))
    uvicorn_logger.addHandler(uvicorn_console)
    
    # File handler for uvicorn
    uvicorn_handler = logging.handlers.RotatingFileHandler(
        log_dir / "uvicorn.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    uvicorn_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    uvicorn_handler.setFormatter(uvicorn_formatter)
    uvicorn_logger.addHandler(uvicorn_handler)
    
    # Uvicorn access logger
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = False
    uvicorn_access_logger.setLevel(logging.INFO)
    
    # Add UTF-8 console handler for uvicorn.access
    uvicorn_access_console = Utf8StreamHandler(sys.stdout)
    uvicorn_access_console.setLevel(logging.INFO)
    uvicorn_access_console.setFormatter(logging.Formatter(SIMPLE_LOG_FORMAT))
    uvicorn_access_logger.addHandler(uvicorn_access_console)
    
    # File handler for uvicorn access
    uvicorn_access_handler = logging.handlers.RotatingFileHandler(
        log_dir / "uvicorn_access.log",
        maxBytes=LOG_MAX_SIZE,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    uvicorn_access_formatter = logging.Formatter(DETAILED_LOG_FORMAT)
    uvicorn_access_handler.setFormatter(uvicorn_access_formatter)
    uvicorn_access_logger.addHandler(uvicorn_access_handler)
    
    # Uvicorn error logger
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.propagate = False
    uvicorn_error_logger.setLevel(logging.INFO)
    
    # Add UTF-8 console handler for uvicorn.error
    uvicorn_error_console = Utf8StreamHandler(sys.stderr)
    uvicorn_error_console.setLevel(logging.WARNING)
    uvicorn_error_console.setFormatter(logging.Formatter(SIMPLE_LOG_FORMAT))
    uvicorn_error_logger.addHandler(uvicorn_error_console)
    
    # Reuse uvicorn file handler for errors too
    uvicorn_error_logger.addHandler(uvicorn_handler)
    
    # ===== THIRD-PARTY LOGGERS =====
    # Configure external library log levels to reduce noise
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.INFO)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    _logging_initialized = True
    
    # Create main application logger and log initialization
    app_logger = logging.getLogger("amzurqastra.config")
    app_logger.info("=" * 60)
    app_logger.info("AmzurQAstra Comprehensive Logging System Initialized")
    app_logger.info("=" * 60)
    app_logger.info(f"Log Level: {LOG_LEVEL}")
    app_logger.info(f"Log Directory: {log_dir.absolute()}")
    app_logger.info(f"Console Logging: {ENABLE_CONSOLE_LOGGING}")
    app_logger.info(f"Performance Logging: {ENABLE_PERFORMANCE_LOGGING}")
    app_logger.info(f"Request Logging: {ENABLE_REQUEST_LOGGING}")
    app_logger.info(f"SQL Logging: {ENABLE_SQL_LOGGING}")
    app_logger.info(f"SQL Log Level: {SQL_LOG_LEVEL}")
    app_logger.info(f"SQL Results Logging: {LOG_SQL_RESULTS}")
    app_logger.info(f"Unicode/Emoji Support: Enabled (UTF-8 with safe encoding)")
    app_logger.info(f"Log Files Created:")
    app_logger.info(f"  - app.log (Main application logs)")
    app_logger.info(f"  - performance.log (Performance metrics)")
    app_logger.info(f"  - error.log (Errors and exceptions)")
    app_logger.info(f"  - requests.log (HTTP requests/responses)")
    app_logger.info(f"  - debug.log (Debug information)")
    app_logger.info(f"  - uvicorn.log (Server logs)")
    app_logger.info(f"  - uvicorn_access.log (Access logs)")
    app_logger.info(f"  - qastra_sql.log (SQL queries and database operations)")
    app_logger.info(f"  - backend/logs/bic.log (Build Integrity Check - for QA debugging)")
    app_logger.info("=" * 60)
    
    return app_logger

def get_logger(name: str):
    """Get a logger instance with consistent naming convention."""
    return logging.getLogger(f"amzurqastra.{name}")

def log_performance(operation: str, duration_ms: float, **kwargs):
    """Log performance metrics."""
    if not ENABLE_PERFORMANCE_LOGGING:
        return
        
    perf_logger = logging.getLogger("performance")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    message = f"{operation} completed in {duration_ms:.2f}ms"
    if extra_info:
        message += f" | {extra_info}"
    perf_logger.info(message)

def log_error(error: Exception, context: str = "", **kwargs):
    """Log errors with full context and stack trace."""
    error_logger = logging.getLogger("error")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    message = f"ERROR in {context}: {type(error).__name__}: {str(error)}"
    if extra_info:
        message += f" | Context: {extra_info}"
    error_logger.error(message, exc_info=True)

def log_debug(message: str, **kwargs):
    """Log debug information."""
    debug_logger = logging.getLogger("debug")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    full_message = message
    if extra_info:
        full_message += f" | {extra_info}"
    debug_logger.debug(full_message)

def log_request(method: str, path: str, status_code: int, duration_ms: float, **kwargs):
    """Log HTTP request details."""
    if not ENABLE_REQUEST_LOGGING:
        return
        
    request_logger = logging.getLogger("requests")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    message = f"{method} {path} | {status_code} | {duration_ms:.2f}ms"
    if extra_info:
        message += f" | {extra_info}"
    request_logger.info(message)

def log_sql_query(query: str, params=None, duration_ms: float = None, **kwargs):
    """Log SQL query execution with optional performance timing."""
    if not ENABLE_SQL_LOGGING:
        return
        
    sql_logger = logging.getLogger("sql")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    
    # Clean up the query for logging (remove extra whitespace)
    clean_query = " ".join(query.split())
    
    message = f"QUERY: {clean_query}"
    
    if params:
        message += f" | PARAMS: {params}"
    
    if duration_ms is not None:
        message += f" | DURATION: {duration_ms:.2f}ms"
    
    if extra_info:
        message += f" | {extra_info}"
    
    sql_logger.info(message)

def log_sql_result(query: str, row_count: int, duration_ms: float = None, **kwargs):
    """Log SQL query results."""
    if not ENABLE_SQL_LOGGING or not LOG_SQL_RESULTS:
        return
        
    sql_logger = logging.getLogger("sql")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    
    # Clean up the query for logging
    clean_query = " ".join(query.split())
    
    message = f"RESULT: {clean_query} | ROWS: {row_count}"
    
    if duration_ms is not None:
        message += f" | DURATION: {duration_ms:.2f}ms"
    
    if extra_info:
        message += f" | {extra_info}"
    
    sql_logger.info(message)

def log_sql_error(query: str, error: Exception, **kwargs):
    """Log SQL query errors."""
    if not ENABLE_SQL_LOGGING:
        return
        
    sql_logger = logging.getLogger("sql")
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    
    # Clean up the query for logging
    clean_query = " ".join(query.split())
    
    message = f"ERROR: {clean_query} | {type(error).__name__}: {str(error)}"
    
    if extra_info:
        message += f" | {extra_info}"
    
    sql_logger.error(message, exc_info=True)