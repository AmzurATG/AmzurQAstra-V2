"""Pydantic schemas for gap analysis API and LLM output validation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class GapAnalysisRunCreate(BaseModel):
    project_id: int
    requirement_id: int


class GapItem(BaseModel):
    type: str = "unknown"
    detail: str = ""
    related_story_key: Optional[str] = None


class SuggestedUserStory(BaseModel):
    title: str = Field(..., max_length=500)
    description: str = ""
    acceptance_criteria: str = ""
    rationale: str = ""


class GapAnalysisLlmResult(BaseModel):
    summary: str = ""
    coverage_estimate_percent: Optional[float] = None
    gaps: List[GapItem] = Field(default_factory=list)
    suggested_user_stories: List[SuggestedUserStory] = Field(default_factory=list)
    notes: str = ""


class GapAnalysisRunResponse(BaseModel):
    id: int
    project_id: int
    requirement_id: int
    created_by: Optional[int] = None
    status: str
    result_json: Optional[dict] = None
    error_message: Optional[str] = None
    pdf_path: Optional[str] = None
    requirement_title: Optional[str] = None
    requirement_file_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AcceptGapSuggestionsRequest(BaseModel):
    indices: List[int] = Field(..., min_length=1)
