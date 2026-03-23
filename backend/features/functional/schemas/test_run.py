"""
Test Run Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from features.functional.db.models.test_run import TestRunStatus
from features.functional.db.models.test_result import TestResultStatus


class TestRunBase(BaseModel):
    """Base test run schema."""
    name: Optional[str] = None
    description: Optional[str] = None


class TestRunCreate(TestRunBase):
    """Schema for creating a test run."""
    project_id: int
    test_case_ids: Optional[List[int]] = None  # If None, run all test cases
    browser: str = "chromium"
    headless: bool = True
    config: Optional[Dict[str, Any]] = None


class TestRunResponse(TestRunBase):
    """Schema for test run response."""
    id: int
    project_id: int
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
    """Schema for test result response."""
    id: int
    test_run_id: int
    test_case_id: int
    status: TestResultStatus
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    failed_step: Optional[int] = None
    screenshot_path: Optional[str] = None
    step_results: Optional[List[Dict[str, Any]]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TestRunDetailResponse(TestRunResponse):
    """Test run with all results."""
    results: List[TestResultResponse] = []
