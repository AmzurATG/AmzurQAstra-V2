"""
Test Case Schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from features.functional.db.models.test_case import (
    TestCasePriority,
    TestCaseCategory,
    TestCaseStatus,
    TestCaseSource,
)
from features.functional.schemas.test_step import TestStepResponse


class TestCaseBase(BaseModel):
    """Base test case schema."""
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    priority: TestCasePriority = TestCasePriority.medium
    category: TestCaseCategory = TestCaseCategory.regression


class TestCaseCreate(TestCaseBase):
    """Schema for creating a test case."""
    project_id: int
    requirement_id: Optional[int] = None
    user_story_id: Optional[int] = None
    status: TestCaseStatus = TestCaseStatus.draft
    tags: Optional[str] = None
    integrity_check: bool = False


class TestCaseUpdate(BaseModel):
    """Schema for updating a test case."""
    title: Optional[str] = None
    description: Optional[str] = None
    preconditions: Optional[str] = None
    priority: Optional[TestCasePriority] = None
    category: Optional[TestCaseCategory] = None
    status: Optional[TestCaseStatus] = None
    tags: Optional[str] = None
    integrity_check: Optional[bool] = None


class UserStoryBrief(BaseModel):
    """Brief user story info for test case response."""
    id: int
    external_key: Optional[str] = None
    title: str
    item_type: str
    
    class Config:
        from_attributes = True


class TestCaseResponse(TestCaseBase):
    """Schema for test case response."""
    id: int
    case_number: int
    project_id: int
    requirement_id: Optional[int] = None
    user_story_id: Optional[int] = None
    user_story: Optional[UserStoryBrief] = None
    status: TestCaseStatus
    tags: Optional[str] = None
    is_automated: bool
    is_generated: bool
    source: TestCaseSource = TestCaseSource.manual
    integrity_check: bool = False
    jira_key: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    steps_count: int = 0
    
    class Config:
        from_attributes = True


class TestCaseWithSteps(TestCaseResponse):
    """Test case with all steps."""
    steps: List[TestStepResponse] = []


class GenerateTestCasesRequest(BaseModel):
    """Request for generating test cases."""
    project_id: int
    requirement_id: Optional[int] = None
    jira_keys: Optional[List[str]] = None
    azure_work_item_ids: Optional[List[int]] = None
    custom_prompt: Optional[str] = None
