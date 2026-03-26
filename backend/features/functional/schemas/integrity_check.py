"""
Integrity Check Schemas
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel


class IntegrityCheckCredentials(BaseModel):
    """Credentials for integrity check."""
    username: Optional[str] = None
    password: Optional[str] = None
    login_url: Optional[str] = None
    username_selector: Optional[str] = None
    password_selector: Optional[str] = None
    submit_selector: Optional[str] = None


class CriticalPage(BaseModel):
    """Critical page to check."""
    name: str
    url: str
    expected_elements: Optional[List[str]] = None  # Selectors to verify


class IntegrityCheckRequest(BaseModel):
    """Request for integrity check."""
    project_id: int
    app_url: str
    credentials: Optional[IntegrityCheckCredentials] = None
    critical_pages: Optional[List[CriticalPage]] = None
    take_screenshots: bool = True
    # app_form = email/password on your app's login page; google_sso = open app's "Sign in with Google" then fill Google account creds
    login_mode: Literal["app_form", "google_sso"] = "app_form"
    browser_engine: Optional[Literal["playwright", "steel"]] = None


class PageCheckResult(BaseModel):
    """Result of checking a single page."""
    name: str
    url: str
    status: str  # "passed", "failed", "error"
    load_time_ms: Optional[int] = None
    screenshot_path: Optional[str] = None
    missing_elements: Optional[List[str]] = None
    error: Optional[str] = None


class StepResult(BaseModel):
    """Result of executing a single test step."""
    step_number: int
    action: str
    description: Optional[str] = None
    status: str  # "passed", "failed", "error"
    duration_ms: int
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    # LLM diagnosis populated by Gemini when the step fails
    llm_diagnosis: Optional[str] = None


class TestCaseResult(BaseModel):
    """Result of executing a test case for integrity check."""
    test_case_id: int
    title: str
    status: str  # "passed", "failed", "error"
    steps_total: int
    steps_passed: int
    steps_failed: int
    step_results: List[StepResult]
    duration_ms: int
    error: Optional[str] = None


class IntegrityCheckResponse(BaseModel):
    """Response from integrity check."""
    project_id: int
    status: str  # "passed", "failed", "error"
    app_reachable: bool
    login_successful: Optional[bool] = None
    login_error: Optional[str] = None
    login_llm_diagnosis: Optional[str] = None
    # Test case results
    test_cases_total: int = 0
    test_cases_passed: int = 0
    test_cases_failed: int = 0
    test_case_results: List[TestCaseResult] = []
    # Legacy page results (for backward compatibility)
    pages_checked: int = 0
    pages_passed: int = 0
    pages_failed: int = 0
    page_results: List[PageCheckResult] = []
    screenshots: List[str] = []
    duration_ms: int
    checked_at: datetime
    error: Optional[str] = None
