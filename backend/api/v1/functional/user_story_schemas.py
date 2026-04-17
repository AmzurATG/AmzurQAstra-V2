"""Pydantic schemas for User Stories API."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from common.db.models.user_story import (
    UserStoryStatus,
    UserStoryPriority,
    UserStoryItemType,
)


class UserStoryCreate(BaseModel):
    project_id: int
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: UserStoryStatus = UserStoryStatus.open
    priority: UserStoryPriority = UserStoryPriority.medium
    item_type: UserStoryItemType = UserStoryItemType.story
    parent_key: Optional[str] = None
    story_points: Optional[int] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    integrity_check: bool = False


class UserStoryUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: Optional[UserStoryStatus] = None
    priority: Optional[UserStoryPriority] = None
    item_type: Optional[UserStoryItemType] = None
    parent_key: Optional[str] = None
    story_points: Optional[int] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    integrity_check: Optional[bool] = None


class UserStoryResponse(BaseModel):
    id: int
    project_id: int
    external_id: Optional[str]
    external_key: Optional[str]
    external_url: Optional[str]
    source: str
    integration_id: Optional[int]
    title: str
    description: Optional[str]
    acceptance_criteria: Optional[str]
    status: str
    priority: str
    item_type: str
    parent_key: Optional[str]
    story_points: Optional[int]
    assignee: Optional[str]
    reporter: Optional[str]
    labels: Optional[List[str]]
    sprint_id: Optional[str] = None
    sprint_name: Optional[str] = None
    integrity_check: bool = False
    linked_test_cases: int = 0
    generated_test_cases: int = 0
    linked_requirements: int = 0
    last_synced_at: Optional[datetime]
    external_updated_at: Optional[datetime]
    external_created_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    integration_type: str
    project_key: Optional[str] = None
    sprint_id: Optional[int] = None
    # When set (non-empty), Jira uses sprint in (...); takes precedence over sprint_id.
    sprint_ids: Optional[List[int]] = None
    issue_types: Optional[List[str]] = None
    updated_since: Optional[datetime] = None
    force_full_sync: bool = False


class SyncResponse(BaseModel):
    status: str
    message: str
    items_synced: int
    errors: List[str] = []


class StoryStatsResponse(BaseModel):
    total: int
    open: int
    in_progress: int
    done: int
    blocked: int


class SprintResponse(BaseModel):
    id: int
    name: str
    state: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DeleteUserStoryResponse(BaseModel):
    message: str
    test_cases_deleted: int


class GenerateTestsRequest(BaseModel):
    include_steps: bool = True
    force_regenerate: bool = False


class GeneratedTestCaseInfo(BaseModel):
    id: int
    case_number: int
    title: str
    priority: str
    category: str


class GenerateTestsResponse(BaseModel):
    success: bool
    user_story_id: int
    user_story_key: Optional[str] = None
    test_cases_created: int = 0
    test_cases: List[GeneratedTestCaseInfo] = []
    error: Optional[str] = None
    code: Optional[str] = None
