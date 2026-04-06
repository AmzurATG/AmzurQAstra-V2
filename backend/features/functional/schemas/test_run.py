"""
Test Run Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from features.functional.db.models.test_run import TestRunStatus
from features.functional.db.models.test_result import TestResultStatus


# ── Create / Config ──────────────────────────────────────────────────────────

class TestRunCredentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class TestRunCreate(BaseModel):
    project_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    test_case_ids: Optional[List[int]] = None
    app_url: Optional[str] = None
    credentials: Optional[TestRunCredentials] = None
    use_google_signin: bool = False
    browser: str = "chromium"
    headless: bool = False
    config: Optional[Dict[str, Any]] = None


class TestRunStartResponse(BaseModel):
    run_id: int
    status: str


class TestRunSummaryResponse(BaseModel):
    """Project-wide run counts (not limited by pagination)."""
    total: int
    passed: int
    failed: int
    running: int
    pending: int
    cancelled: int
    avg_pass_rate: int


# ── Responses ────────────────────────────────────────────────────────────────

class TestRunResponse(BaseModel):
    id: int
    project_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    status: TestRunStatus
    triggered_by: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    browser: str
    report_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    id: int
    test_run_id: int
    test_case_id: int
    status: TestResultStatus
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    failed_step: Optional[int] = None
    screenshot_path: Optional[str] = None
    step_results: Optional[List[Dict[str, Any]]] = None
    adapted_steps: Optional[List[Dict[str, Any]]] = None
    original_steps: Optional[List[Dict[str, Any]]] = None
    agent_logs: Optional[List[Dict[str, Any]]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TestRunDetailResponse(TestRunResponse):
    results: List[TestResultResponse] = []


# ── Live Progress (polling) ──────────────────────────────────────────────────

class LogEntry(BaseModel):
    timestamp: str
    level: str = "info"
    message: str
    test_case_id: Optional[int] = None


class CompletedCaseResult(BaseModel):
    test_result_id: int
    test_case_id: int
    title: str
    status: str
    steps_total: int
    steps_passed: int
    steps_failed: int
    duration_ms: int
    step_results: Optional[List[Dict[str, Any]]] = None
    adapted_steps: Optional[List[Dict[str, Any]]] = None
    original_steps: Optional[List[Dict[str, Any]]] = None
    agent_logs: Optional[List[Dict[str, Any]]] = None
    screenshot_path: Optional[str] = None
    agent_screenshot_count: Optional[int] = None
    has_adaptations: Optional[bool] = None


class LiveProgressResponse(BaseModel):
    run_id: int
    status: str
    percentage: int = 0
    current_test_case_index: int = 0
    total_test_cases: int = 0
    current_test_case_title: Optional[str] = None
    current_step_info: Optional[str] = None
    completed_results: List[CompletedCaseResult] = []
    logs: List[LogEntry] = []
    error: Optional[str] = None
