"""Pydantic schemas for BRD → User Story generation API."""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class BrdModule(BaseModel):
    """A functional module / theme extracted from the BRD."""
    label: str
    scope: str


class SuggestedStory(BaseModel):
    """A user story suggested from a BRD document."""
    title: str = Field(..., max_length=120)
    description: str = ""
    acceptance_criteria: str = ""
    priority: str = "medium"
    module: str = ""
    rationale: str = ""
    discovery_source: str = Field(default="brd_generated", description="brd_generated | ui_discovered | brd_ui_merged")


class GenerateStoriesFromBrdRequest(BaseModel):
    project_id: int
    requirement_id: int
    max_stories: int = Field(default=20, ge=5, le=60)
    include_ui_context: bool = Field(default=True, description="Merge UI discovery inventory when available")


class GenerateStoriesFromBrdResponse(BaseModel):
    requirement_id: int
    modules_identified: int
    stories: List[SuggestedStory]
    total_stories: int


class AcceptBrdStoriesRequest(BaseModel):
    project_id: int
    requirement_id: int
    stories: List[SuggestedStory] = Field(
        ...,
        description="Full stories array from generate-stories response.",
    )
    indices: Optional[List[int]] = Field(
        default=None,
        description="Specific story indices to accept. Omit (or set null) to accept all.",
    )


class AcceptBrdStoriesResponse(BaseModel):
    created: int
    story_ids: List[int]
    errors: List[str] = []
