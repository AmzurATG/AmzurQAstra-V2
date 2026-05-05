import os
import sys
import asyncio
import logging
import uvicorn
import multiprocessing
import time
import json
from datetime import datetime

# ===== FORCE UTF-8 ENCODING IMMEDIATELY =====
# This MUST happen before any logging or imports that might log
# Critical for Windows compatibility with emoji characters
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

# ===== INITIALIZE LOGGING FIRST =====
# Import and setup logging before any other heavy imports
from config import setup_logging, get_logger, log_performance, log_error, log_debug, log_request, log_sql_query, log_sql_result, log_sql_error

# Initialize comprehensive logging system
app_logger = setup_logging()

# Environment profiler - runs before heavy imports to diagnose issues
if getattr(sys, 'frozen', False):
    # Only profile in frozen executable
    try:
        from utils.environment_profiler import profile_environment
        profile_data, failed_packages = profile_environment()
        if failed_packages:
            app_logger.warning(f"Some packages failed to load: {', '.join(failed_packages)}")
            app_logger.warning("The application may not function correctly.")
            app_logger.warning("Check environment_profile.log for details.")
            print(f"\n⚠ WARNING: Some packages failed to load: {', '.join(failed_packages)}")
            print("The application may not function correctly.")
            print("Check environment_profile.log for details.\n")
    except Exception as e:
        app_logger.error(f"Environment profiling failed: {e}")
        print(f"Environment profiling failed: {e}")

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import tempfile
from pathlib import Path
import google.generativeai as genai
from services.universal_llm_logger import log_openai_call
from services.document_processor import DocumentProcessor
from services.recommendation_engine import TestingRecommendationEngine, format_recommendations_for_report, TEST_TEMPLATES
from routes.login_type_routes import router as login_type_router
from routes.build_integrity_routes import router as bic_router  # Import the BIC router
from routes.mcp_routes import router as mcp_router  # NEW: MCP server routes
from routes.test_execution_routes import router as test_execution_router  # Multi-agent test execution
from routes.test_execution_routes import router_no_prefix as test_execution_router_no_prefix  # Without /api prefix
from routes.auth_routes import router as auth_router  # Authentication routes
from routes.audit_logs_routes import router as audit_logs_router  # Audit logs routes

from routes.subscription import router as subscription_router
from routes import checkout  # Import the new router
from services.supabase_audit_service import SupabaseAuditService
from services.supabase_bic_service import SupabaseBICService
from routes.email_notification_routes import router as email_notification_router
from routes.selector_logs_routes import router as selector_logs_router, router_no_prefix as selector_logs_router_no_prefix
from routes.bic_summary_routes import router as bic_summary_router
from routes.test_reports_routes import router as test_reports_router
from routes.test_recommendations_routes import router as test_recommendations_router

from routes.testcases_routes import router as testcases_router  # Import test cases routes
from routes.userstories_routes import router as userstories_router  # Import user stories routes
from routes.build_integrity_routes import router as bic_router  # Import the BIC router
from routes import gap_analysis
from routes.gap_analysis import router as gap_analysis_router
from routes.userstories_routes import router as userstories_router
from routes.profile_routes import router as profile_router  # Import profile routes
from routes.user_story_status import router as user_story_status_router

# Import shared storage for consistency across routes
from utils.shared_storage import  processing_results

from routes.profile_routes import router as profile_router  # Import profile routes

# Import new BRD analysis services
from services.recommendation_engine import TestingRecommendationEngine, format_recommendations_for_report

# Fix for Windows asyncio subprocess issue - MUST be set before any async operations
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Load environment variables from .env file
# In frozen mode (PyInstaller), load from executable's directory since CWD may differ
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    env_path = os.path.join(exe_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        app_logger.info(f"Loaded .env from executable directory: {env_path}")
        print(f"✓ Loaded .env from executable directory: {env_path}")
    else:
        app_logger.warning(f".env file not found at {env_path}")
        app_logger.warning("Please ensure .env file exists in the same folder as the executable.")
        print(f"⚠️ WARNING: .env file not found at {env_path}")
        print("  Please ensure .env file exists in the same folder as the executable.")
        load_dotenv()  # Try default anyway
else:
    load_dotenv()

# Optional Supabase import with error handling for recommendation engine
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
    app_logger.info("Supabase client library loaded successfully")
except ImportError as e:
    SUPABASE_AVAILABLE = False
    Client = None
    app_logger.warning(f"Supabase not available: {e}")
    print(f"Warning: Supabase not available: {e}")
except Exception as e:
    SUPABASE_AVAILABLE = False
    Client = None
    app_logger.error(f"Supabase import failed: {e}")
    print(f"Warning: Supabase import failed: {e}")

# Text extraction imports for recommendation engine
try:
    import PyPDF2
    from docx import Document
    HAS_PDF_DOCX = True
    app_logger.info("PDF/DOCX processing libraries loaded successfully")
except ImportError:
    HAS_PDF_DOCX = False
    app_logger.warning("PDF/DOCX processing libraries not available")

try:
    # import textract  # Optional - not always available
    HAS_TEXTRACT = False  # Disabled for now
except ImportError:
    HAS_TEXTRACT = False

HAS_TEXT_EXTRACTION = HAS_PDF_DOCX or HAS_TEXTRACT

# Create logger for main module
logger = get_logger("main")

# Create FastAPI app
app = FastAPI(title="QAstra API")

# ===== COMPREHENSIVE LOGGING MIDDLEWARE =====

@app.middleware("http")
async def comprehensive_logging_middleware(request: Request, call_next):
    """
    Comprehensive HTTP request/response logging and performance tracking.
    Logs all requests, responses, performance metrics, and errors.
    """
    # Start timing
    start_time = time.time()
    
    # Extract request information
    method = request.method
    url = str(request.url)
    path = request.url.path
    query_params = str(request.query_params) if request.query_params else ""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    content_type = request.headers.get("content-type", "")
    content_length = request.headers.get("content-length", "0")
    
    # Extract user information from JWT token if available
    user_id = "anonymous"
    user_email = "unknown"
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # You can decode JWT here to extract user info if needed
            user_id = "authenticated"
            user_email = "authenticated_user"
    except Exception as e:
        log_debug("Failed to extract user info from token", error=str(e))
    
    # Generate unique request ID for tracking
    request_id = f"req_{int(time.time() * 1000)}_{id(request) % 10000}"
    
    # Log request start
    logger.info(f"REQUEST START [{request_id}] | {method} {path}")
    log_debug(f"Request details [{request_id}]", 
             method=method, path=path, query=query_params,
             client_ip=client_ip, user_agent=user_agent[:100],
             content_type=content_type, content_length=content_length,
             user_id=user_id, user_email=user_email)
    
    # Process request and handle exceptions
    response = None
    error_occurred = False
    status_code = 500
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        
    except HTTPException as http_exc:
        error_occurred = True
        status_code = http_exc.status_code
        log_error(http_exc, f"HTTP Exception in request [{request_id}]", 
                 method=method, path=path, user_id=user_id, client_ip=client_ip,
                 status_code=status_code)
        # Re-raise to let FastAPI handle it
        raise
        
    except Exception as exc:
        error_occurred = True
        status_code = 500
        log_error(exc, f"Unhandled exception in request [{request_id}]", 
                 method=method, path=path, user_id=user_id, client_ip=client_ip)
        # Create error response
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id}
        )
        
    finally:
        # Calculate duration
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Log response
        logger.info(f"REQUEST END [{request_id}] | {method} {path} | {status_code} | {duration_ms:.2f}ms")
        
        # Log detailed request information
        log_request(method, path, status_code, duration_ms,
                   request_id=request_id, user_id=user_id, user_email=user_email,
                   client_ip=client_ip, query_params=query_params)
        
        # Log performance metrics
        log_performance(f"HTTP_{method}_{path.replace('/', '_').strip('_')}", 
                       duration_ms,
                       status_code=status_code, user_id=user_id,
                       client_ip=client_ip, request_id=request_id)
        
        # Log slow requests as warnings
        if duration_ms > 5000:  # 5 seconds
            logger.warning(f"SLOW REQUEST [{request_id}] | {method} {path} | {duration_ms:.2f}ms | {status_code}")
        
        # Log error requests
        if error_occurred:
            logger.error(f"ERROR REQUEST [{request_id}] | {method} {path} | {status_code} | {duration_ms:.2f}ms")
    
    return response

# ===== COMPREHENSIVE EXCEPTION HANDLERS =====

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with comprehensive error logging."""
    
    # Generate error ID for tracking
    error_id = f"err_{int(time.time() * 1000)}"
    
    # Log the error with full context
    log_error(exc, f"Global exception handler [{error_id}]", 
             method=request.method, path=request.url.path,
             client_ip=request.client.host if request.client else "unknown",
             error_id=error_id)
    
    # Log to main logger as well
    logger.error(f"UNHANDLED EXCEPTION [{error_id}] | {request.method} {request.url.path} | {type(exc).__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler with detailed logging."""
    
    error_id = f"http_err_{int(time.time() * 1000)}"
    
    # Log HTTP errors
    if exc.status_code >= 400:
        level_name = "ERROR" if exc.status_code >= 500 else "WARNING"
        level = getattr(logging, level_name)
        logger.log(level,
            f"HTTP EXCEPTION [{error_id}] | {request.method} {request.url.path} | {exc.status_code} | {exc.detail}"
        )
        
        # Log additional context for server errors
        if exc.status_code >= 500:
            log_error(Exception(exc.detail), f"HTTP 5xx error [{error_id}]", 
                     method=request.method, path=request.url.path,
                     status_code=exc.status_code, error_id=error_id)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Configure CORS - Allow all origins for Electron app compatibility
# The Electron app loads from file:// which sends 'null' as origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Electron and development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Lockout-Seconds"],
)

# Initialize audit service (using local SQLite for debugging)
# audit_service = SupabaseAuditService()
audit_service = SupabaseAuditService()

# Initialize Supabase BIC service
bic_service = None
try:
    bic_service = SupabaseBICService()
    logger.info("Supabase BIC service initialized successfully")
except Exception as e:
    log_error(e, "Failed to initialize Supabase BIC service")
    bic_service = None

# Initialize BRD analysis services with unified document processor

# Initialize unified document processor (contains all features)
document_processor = DocumentProcessor()
logger.info("Document processor initialized")

# Initialize new simplified recommendation engine
testing_recommendation_engine = TestingRecommendationEngine()
logger.info("Testing recommendation engine initialized")

# Initialize Supabase for recommendation engine (optional)
supabase = None
try:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if SUPABASE_AVAILABLE and supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully for recommendation engine")
    else:
        logger.warning("Supabase credentials not found or not available for recommendation engine")
except Exception as e:
    log_error(e, "Failed to initialize Supabase client for recommendation engine")

# Initialize LiteLLM client (Primary)
litellm_client = None
try:
    from services.litellm_client import get_litellm_client
    litellm_client = get_litellm_client()
    logger.info("LiteLLM client initialized successfully")
except Exception as e:
    log_error(e, "Failed to initialize LiteLLM client")

# Initialize Gemini AI (Fallback)
gemini_api_key = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_TEXT = "gemini-2.0-flash"  # For text generation

if gemini_api_key:
    try:
        genai.configure(api_key=gemini_api_key)
        logger.info("Gemini AI (fallback) initialized successfully")
    except Exception as e:
        log_error(e, "Failed to initialize Gemini AI")
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

# Initialize OpenAI client for comparison functionality (Fallback)
openai_client = None
OPENAI_MODEL_TEXT = "gpt-4o-mini"
try:
    import openai
    
    # Try LiteLLM first
    litellm_openai_key = os.getenv("LITELLM_OPENAI_API_KEY")
    litellm_proxy_url = os.getenv("LITELLM_PROXY_URL", "https://litellm.amzur.com")
    
    if litellm_openai_key:
        openai_client = openai.OpenAI(
            api_key=litellm_openai_key,
            base_url=litellm_proxy_url
        )
        logger.info("OpenAI client initialized with LiteLLM proxy")
    else:
        # Fallback to direct OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            openai_client = openai.OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized with direct API (fallback)")
        else:
            logger.warning("No OpenAI configuration found")
            
except ImportError:
    logger.warning("OpenAI library not installed")
except Exception as e:
    log_error(e, "Failed to initialize OpenAI client")

# Create directories for BRD storage
BRD_UPLOADS_DIR = Path("uploads")
BRD_UPLOADS_DIR.mkdir(exist_ok=True, parents=True)

SDLC_DOCS_DIR = Path("uploads/sdlc_docs").resolve()
SDLC_DOCS_DIR.mkdir(exist_ok=True, parents=True)
# Create upload directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)

bearer_scheme = HTTPBearer(auto_error=False)

# Include routers - Auth routes MUST be first to avoid conflicts
app.include_router(auth_router, tags=["authentication"])  # Authentication routes (login, signup, password reset)
app.include_router(subscription_router, tags=["subscription"])  # Subscription routes
app.include_router(audit_logs_router, tags=["audit"])  # Include audit routes
app.include_router(testcases_router, prefix="/api", tags=["test-cases"])  # Include test cases routes
app.include_router(email_notification_router, prefix="/api", tags=["email-notifications"])
app.include_router(checkout.router, prefix="/stripe", tags=["stripe"])
app.include_router(login_type_router)
app.include_router(bic_router, prefix="/api", tags=["build-check"])
app.include_router(mcp_router)  # NEW: MCP server routes for test automation engine
app.include_router(test_execution_router, tags=["test-execution"])  # Multi-agent workflow with /api prefix
app.include_router(test_execution_router_no_prefix, tags=["test-execution"])  # Multi-agent workflow without /api prefix
app.include_router(gap_analysis_router, tags=["gap-analysis"])  # Gap analysis, BRD processing, JIRA integration
app.include_router(userstories_router, tags=["user-stories"])  # User stories management
app.include_router(bic_router, prefix="/api", tags=["build-integrity-check"])  # Include the BIC router
app.include_router(test_recommendations_router, prefix="/api", tags=["test-recommendations"])  # Test recommendations routes
# Include both routers
app.include_router(selector_logs_router, tags=["selector-logs"])  # NEW: Selector logs routes with /api prefix
# Include both routers
app.include_router(selector_logs_router, tags=["selector-logs"])  # NEW: Selector logs routes with /api prefix
app.include_router(selector_logs_router_no_prefix, tags=["selector-logs"])  # NEW: Selector logs routes without /api prefix
app.include_router(profile_router, prefix="/api", tags=["profile"])  # Include profile routes
 # NEW: Jira bug management routes

# Include the user story status router
app.include_router(user_story_status_router)

app.include_router(audit_logs_router, prefix="/audit", tags=["audit-logs"])  # Enhanced audit logs endpoints
app.include_router(audit_logs_router, prefix="/api/audit", tags=["audit-logs-api"])  # Alternative API prefix for audit logs
app.include_router(bic_summary_router, prefix="/api/bic-summaries", tags=["bic-summary-api"])  # BIC summary endpoints with /api prefix
app.include_router(bic_summary_router, prefix="/bic-summaries", tags=["bic-summary"])  # BIC summary endpoints (proxy strips /api)
app.include_router(test_reports_router, prefix="/reports", tags=["test-reports"])  # Test reports endpoints (proxy strips /api)
app.include_router(test_reports_router, prefix="/api/reports", tags=["test-reports-api"])  # Test reports with /api prefix for Electron

# Also include test reports router without prefix for backward compatibility
app.include_router(test_reports_router, prefix="/reports", tags=["test-reports-compat"])  # Test reports compatibility endpoints

# ===== ENHANCED STARTUP/SHUTDOWN EVENTS =====

@app.on_event("startup")
async def startup_event():
    """Enhanced startup event with comprehensive logging."""
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("[START] AmzurQAstra API Server Starting Up")
    logger.info("=" * 80)
    
    try:
        logger.info("Initializing Supabase audit service...")
        # Supabase audit service doesn't need database initialization
        # The table should already exist in Supabase
        logger.info("[OK] Supabase audit service ready")
        
        # Try to clean up old audit logs if the method exists
        try:
            if hasattr(audit_service, 'cleanup_old_logs'):
                logger.info("Cleaning up old audit logs...")
                audit_service.cleanup_old_logs(days_to_keep=90)
                logger.info("[OK] Audit logs cleanup completed")
            else:
                logger.info("[WARN] Audit service cleanup method not available - skipping cleanup")
        except Exception as cleanup_error:
            logger.warning(f"[WARN] Audit logs cleanup failed: {cleanup_error}")
        
        # Log environment information
        logger.info(f"Environment: {'PRODUCTION' if os.getenv('ENVIRONMENT') == 'production' else 'DEVELOPMENT'}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Supabase available: {SUPABASE_AVAILABLE}")
        logger.info(f"Text extraction available: {HAS_TEXT_EXTRACTION}")
        
        startup_time = (time.time() - start_time) * 1000
        log_performance("application_startup", startup_time)
        
        logger.info("=" * 80)
        logger.info("[SUCCESS] AmzurQAstra API Server Startup Complete")
        logger.info(f"[TIME] Startup time: {startup_time:.2f}ms")
        logger.info("=" * 80)
        
    except Exception as e:
        log_error(e, "Application startup failed")
        logger.error("[FAIL] AmzurQAstra API Server startup FAILED")
        raise
@app.on_event("shutdown")
async def shutdown_event():
    """Enhanced shutdown event with comprehensive cleanup and logging."""
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("[STOP] AmzurQAstra API Server Shutting Down")
    logger.info("=" * 80)
    
    try:
        logger.info("Cleaning up browser resources...")
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8001/stop", timeout=5.0)
            logger.info("[OK] Browser resources cleaned up")
            
        # Additional cleanup can be added here
        
        shutdown_time = (time.time() - start_time) * 1000
        log_performance("application_shutdown", shutdown_time)
        
        logger.info("=" * 80)
        logger.info("[OK] AmzurQAstra API Server Shutdown Complete")
        logger.info(f"[TIME] Shutdown time: {shutdown_time:.2f}ms")
        logger.info("=" * 80)
        
    except Exception as e:
        log_error(e, "Error during shutdown")
        logger.warning("[WARN] Shutdown completed with warnings")

# Create upload directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/documents", exist_ok=True)

bearer_scheme = HTTPBearer(auto_error=False)

@app.get("/")
async def root():
    """Root endpoint with logging."""
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to QAstra API"}

# ===== LOGGING STATUS ENDPOINT =====

@app.get("/api/logs/status")
async def get_logging_status():
    """Get current logging configuration and status."""
    from config import LOG_LEVEL, LOG_DIR, ENABLE_CONSOLE_LOGGING, ENABLE_PERFORMANCE_LOGGING, ENABLE_REQUEST_LOGGING
    
    logger.info("Logging status requested")
    
    from config import LOG_LEVEL, LOG_DIR, ENABLE_CONSOLE_LOGGING, ENABLE_PERFORMANCE_LOGGING, ENABLE_REQUEST_LOGGING, ENABLE_SQL_LOGGING, SQL_LOG_LEVEL, LOG_SQL_QUERIES, LOG_SQL_RESULTS
    
    logger.info("Logging status requested")
    
    return {
        "status": "active",
        "log_level": LOG_LEVEL,
        "log_directory": LOG_DIR,
        "console_logging": ENABLE_CONSOLE_LOGGING,
        "performance_logging": ENABLE_PERFORMANCE_LOGGING,
        "request_logging": ENABLE_REQUEST_LOGGING,
        "sql_logging": ENABLE_SQL_LOGGING,
        "sql_log_level": SQL_LOG_LEVEL,
        "sql_queries_logging": LOG_SQL_QUERIES,
        "sql_results_logging": LOG_SQL_RESULTS,
        "log_files": [
            "app.log", "performance.log", "error.log", 
            "requests.log", "debug.log", "sql.log",
            "uvicorn.log", "uvicorn_access.log"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

# LLM Configuration - LiteLLM Primary, Direct APIs as Fallback
LLM_API_KEY = os.environ.get("LITELLM_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not LLM_API_KEY:
    logger.warning("No LLM API key found. Set LITELLM_OPENAI_API_KEY or OPENAI_API_KEY.")
    LLM_API_KEY = None

LLM_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini for reliability

# Use LiteLLM proxy if available, otherwise direct OpenAI
if os.environ.get("LITELLM_OPENAI_API_KEY"):
    LLM_API_URL = os.environ.get("LITELLM_PROXY_URL", "https://litellm.amzur.com") + "/chat/completions"
    logger.info("Using LiteLLM proxy for LLM requests")
else:
    LLM_API_URL = "https://api.openai.com/v1/chat/completions"  # Fallback to direct OpenAI
    logger.info("Using direct OpenAI API for LLM requests (fallback)")

#api brd point
@app.get("/api/brd/file/{document_id}")
async def get_brd_file(document_id: str):
    """Get uploaded BRD file by document ID"""
    try:
        logger.info(f"BRD file requested: {document_id}")
        
        if document_id not in processing_results:
            logger.warning(f"BRD document not found: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_info = processing_results[document_id]
        file_path = Path(doc_info["file_path"])
        
        if not file_path.exists():
            logger.error(f"BRD file not found on disk: {file_path}")
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        logger.info(f"Serving BRD file: {file_path.name}")
        
        # Return the file
        return FileResponse(
            path=str(file_path),
            filename=doc_info["filename"],
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, "Error serving BRD file", document_id=document_id)
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")

# Main entry point for running the server
if __name__ == "__main__":
    # Required for Windows multiprocessing with PyInstaller (still needed for other parts)
    multiprocessing.freeze_support()
    
    logger.info("=" * 80)
    logger.info("[FLAG] AmzurQAstra API Backend Main Entry Point")
    logger.info("=" * 80)
    logger.info("[INFO] MCP Server should be started separately using start_mcp_server.py or MCP-Server.exe")
    
    # Detect if running as frozen executable (PyInstaller)
    is_frozen = getattr(sys, 'frozen', False)
    
    logger.info("[WEB] Starting Main Backend on port 8000...")
    logger.info(f"[PACKAGE] Running mode: {'FROZEN EXECUTABLE' if is_frozen else 'DEVELOPMENT'}")
    
    # Create custom uvicorn log config with UTF-8 encoding
    # This ensures uvicorn subprocesses also handle emoji correctly
    uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s | %(levelname)-8s | %(message)s",
            },
            "access": {
                # Use simpler format without client_addr to avoid KeyError
                # The message itself contains the client info from uvicorn
                "format": "%(asctime)s | %(levelname)-8s | %(message)s",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "access",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    if is_frozen:
        # When frozen, pass app object directly (string import doesn't work)
        logger.info("[CONFIG] Using frozen executable configuration")
        uvicorn.run(
            app,  # Pass app object directly
            host="0.0.0.0", 
            port=8000,
            reload=False,  # Must be False in frozen exe
            log_level="info",
            log_config=uvicorn_log_config
        )
    else:
        # Development mode - use string import for hot reload
        logger.info("[CONFIG] Using development configuration with hot reload")
        uvicorn.run(
            "main:app",
            host="0.0.0.0", 
            port=8000,
            reload=True,
            log_level="info",
            log_config=uvicorn_log_config
        )
