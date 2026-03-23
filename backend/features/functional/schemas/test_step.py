"""
Test Step Schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from features.functional.db.models.test_step import TestStepAction


class TestStepBase(BaseModel):
    """Base test step schema."""
    action: TestStepAction
    target: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    expected_result: Optional[str] = None


class TestStepCreate(TestStepBase):
    """Schema for creating a test step."""
    test_case_id: int
    step_number: Optional[int] = None  # Auto-assigned if not provided


class TestStepUpdate(BaseModel):
    """Schema for updating a test step."""
    action: Optional[TestStepAction] = None
    target: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    expected_result: Optional[str] = None
    playwright_code: Optional[str] = None


class TestStepResponse(TestStepBase):
    """Schema for test step response."""
    id: int
    test_case_id: int
    step_number: int
    playwright_code: Optional[str] = None
    selector_type: Optional[str] = None
    selector_confidence: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestStepReorder(BaseModel):
    """Schema for reordering test steps."""
    test_case_id: int
    step_ids: List[int]  # Ordered list of step IDs
