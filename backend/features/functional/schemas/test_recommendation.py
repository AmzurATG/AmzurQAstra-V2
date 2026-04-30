"""Pydantic schemas for test recommendation API and persisted JSON."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TestRecommendationRunCreate(BaseModel):
    project_id: int
    requirement_id: int


class LlmDomainClassificationResult(BaseModel):
    domain_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    intent_summary: str = Field(default="", max_length=4000)


class TestRecommendationRunResponse(BaseModel):
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
