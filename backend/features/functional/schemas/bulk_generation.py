"""Pydantic schemas for bulk test-case generation API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BulkGenerateRequest(BaseModel):
    project_id: int
    story_ids: List[int] = Field(..., min_length=1)
    profile: str = Field(
        default="standard",
        description="Generation profile: light (~5/story), standard (~10/story), comprehensive (~20/story)",
    )
    include_steps: bool = True


class BulkGenerateResponse(BaseModel):
    job_id: int
    status: str
    total_stories: int
    message: str


class GenerationJobStatusResponse(BaseModel):
    job_id: int
    project_id: int
    status: str
    profile: str
    total_stories: int
    completed_stories: int
    current_story_title: Optional[str]
    progress_percent: float
    coverage_report: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoryCoverageItem(BaseModel):
    """Per-story coverage summary in the final job report."""
    story_id: int
    story_title: str
    cases_created: int
    coverage_percent: float
    has_gaps: bool
    scenario_counts: Dict[str, int]
