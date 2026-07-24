"""
Test Run Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

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
    max_concurrency: int = Field(default=6, ge=1, le=6)
    config: Optional[Dict[str, Any]] = None


class TestRunRunAllCreate(BaseModel):
    """Run-all orchestrated execution (LangGraph + local browser lanes)."""
    project_id: int
    app_url: Optional[str] = None
    credentials: Optional[TestRunCredentials] = None
    use_google_signin: bool = False
    headless: bool = False
    test_case_ids: Optional[List[int]] = None


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
    run_number: int
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
    worker_id: Optional[int] = None
    group_id: Optional[str] = None
    status: TestResultStatus
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    failed_step: Optional[int] = None
    screenshot_path: Optional[str] = None
    step_results: Optional[List[Dict[str, Any]]] = None
    adapted_steps: Optional[List[Dict[str, Any]]] = None
    original_steps: Optional[List[Dict[str, Any]]] = None
    agent_logs: Optional[List[Dict[str, Any]]] = None
    ai_modified: Optional[Dict[str, Any]] = None
    jira_bug_key: Optional[str] = None
    jira_bug_url: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TestRunDetailResponse(TestRunResponse):
    results: List[TestResultResponse] = []


class LogJiraBugRequest(BaseModel):
    sprint_id: Optional[int] = None
    summary: Optional[str] = None
    priority: Optional[str] = "Medium"
    attach_screenshots: bool = True


class LogJiraBugResponse(BaseModel):
    key: str
    url: Optional[str] = None
    sprint_id: Optional[int] = None


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
    group_id: Optional[str] = None
    steps_total: int
    steps_passed: int
    steps_failed: int
    setup_skipped_count: Optional[int] = 0
    duration_ms: int
    duration_display: Optional[str] = None
    step_results: Optional[List[Dict[str, Any]]] = None
    adapted_steps: Optional[List[Dict[str, Any]]] = None
    original_steps: Optional[List[Dict[str, Any]]] = None
    agent_logs: Optional[List[Dict[str, Any]]] = None
    screenshot_path: Optional[str] = None
    agent_screenshot_count: Optional[int] = None
    has_adaptations: Optional[bool] = None
    ai_modified: Optional[Dict[str, Any]] = None
    ui_override: Optional[bool] = None
    ui_validation: Optional[Dict[str, Any]] = None
    executor_status: Optional[str] = None
    verdict_source: Optional[str] = None
    infra_error: Optional[bool] = None
    user_message: Optional[str] = None
    error_kind: Optional[str] = None
    error_message: Optional[str] = None
    jira_bug_key: Optional[str] = None
    jira_bug_url: Optional[str] = None


class ActiveLaneInfo(BaseModel):
    worker_id: int
    lane_id: Optional[int] = None
    test_case_id: Optional[int] = None
    title: Optional[str] = None
    step: Optional[str] = None
    step_num: Optional[int] = None
    group_id: Optional[str] = None
    chrome_group: Optional[int] = None
    busy: Optional[bool] = None


class GroupProgressInfo(BaseModel):
    group_id: str
    title: Optional[str] = None
    case_ids: Optional[List[int]] = None
    status: Optional[str] = None
    lane_id: Optional[int] = None


class LiveProgressResponse(BaseModel):
    run_id: int
    run_number: Optional[int] = None
    status: str
    percentage: int = 0
    current_test_case_index: int = 0
    total_test_cases: int = 0
    current_test_case_title: Optional[str] = None
    current_step_info: Optional[str] = None
    completed_results: List[CompletedCaseResult] = []
    logs: List[LogEntry] = []
    error: Optional[str] = None
    active_lanes: List[ActiveLaneInfo] = []
    groups: List[GroupProgressInfo] = []
    live_screenshots: List[str] = []
    ui_desync: Optional[bool] = None
    ui_desync_events: Optional[List[Dict[str, Any]]] = None
    health: Optional[Dict[str, Any]] = None
    health_summary: Optional[str] = None
    supervisor: Optional[Dict[str, Any]] = None
    runtime_banner: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    elapsed_ms: Optional[int] = None
    elapsed_display: Optional[str] = None