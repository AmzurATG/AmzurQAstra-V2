"""
Integrity Check Schemas
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel


# ─── Request ──────────────────────────────────────────────────────────────────

class IntegrityCheckCredentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    login_url: Optional[str] = None
    username_selector: Optional[str] = None
    password_selector: Optional[str] = None
    submit_selector: Optional[str] = None


class CriticalPage(BaseModel):
    name: str
    url: str
    expected_elements: Optional[List[str]] = None


class IntegrityCheckRequest(BaseModel):
    project_id: int
    app_url: str
    credentials: Optional[IntegrityCheckCredentials] = None
    critical_pages: Optional[List[CriticalPage]] = None
    take_screenshots: bool = True
    # When True, the agent follows Google Sign-In / OAuth instead of manual email+password.
    use_google_signin: bool = False


# ─── Async run lifecycle ──────────────────────────────────────────────────────

class RunStartResponse(BaseModel):
    """Returned immediately when a run is started."""
    run_id: str
    status: str  # always "pending" at start


class StepProgressData(BaseModel):
    step_number: int
    description: Optional[str] = None
    screenshot_path: Optional[str] = None


class RunStatusResponse(BaseModel):
    """Returned by the polling endpoint."""
    run_id: str
    status: str                          # pending | running | completed | error | not_found
    percentage: int = 0                  # 0-100
    current_step: Optional[str] = None
    overall_status: Optional[str] = None # passed | failed | error
    screenshots: List[str] = []
    steps: List[Dict[str, Any]] = []
    steps_total: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    summary: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


# ─── Legacy / existing schemas kept for backward compat ──────────────────────

class PageCheckResult(BaseModel):
    name: str
    url: str
    status: str
    load_time_ms: Optional[int] = None
    screenshot_path: Optional[str] = None
    missing_elements: Optional[List[str]] = None
    error: Optional[str] = None


class StepResult(BaseModel):
    step_number: int
    action: str
    description: Optional[str] = None
    status: str
    duration_ms: int
    error: Optional[str] = None
    screenshot_path: Optional[str] = None


class TestCaseResult(BaseModel):
    test_case_id: int
    title: str
    status: str
    steps_total: int
    steps_passed: int
    steps_failed: int
    step_results: List[StepResult]
    duration_ms: int
    error: Optional[str] = None


class IntegrityCheckResponse(BaseModel):
    """Legacy synchronous response — kept for backward compat."""
    project_id: int
    status: str
    app_reachable: bool
    login_successful: Optional[bool] = None
    test_cases_total: int = 0
    test_cases_passed: int = 0
    test_cases_failed: int = 0
    test_case_results: List[TestCaseResult] = []
    pages_checked: int = 0
    pages_passed: int = 0
    pages_failed: int = 0
    page_results: List[PageCheckResult] = []
    screenshots: List[str] = []
    duration_ms: int
    checked_at: datetime
    error: Optional[str] = None


# ─── Preview schemas ──────────────────────────────────────────────────────────

class PreviewStepResponse(BaseModel):
    step_number: int
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    expected_result: Optional[str] = None


class PreviewTestCaseResponse(BaseModel):
    id: int
    case_number: int = 0
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    integrity_check: bool = False
    steps: List[PreviewStepResponse] = []


class PreviewUserStoryResponse(BaseModel):
    id: int
    title: str
    external_key: Optional[str] = None
    status: str
    priority: str
    item_type: str
    integrity_check: bool = False
    test_cases: List[PreviewTestCaseResponse] = []


class IntegrityCheckPreviewResponse(BaseModel):
    user_stories: List[PreviewUserStoryResponse] = []
    standalone_test_cases: List[PreviewTestCaseResponse] = []
    total_user_stories: int = 0
    total_test_cases: int = 0
    total_steps: int = 0
