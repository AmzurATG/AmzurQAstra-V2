"""
BRD → User Story generation API.

Two endpoints:
  POST /requirements/{requirement_id}/generate-stories
      Run the two-pass LLM pipeline; returns preview (not persisted).
  POST /requirements/{requirement_id}/accept-stories
      Accept selected (or all) previewed stories and persist them.

Stories from the preview are passed back by the client in the accept request
because the preview is stateless (not stored server-side between calls).
"""
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.api.deps import get_current_active_user
from common.db.database import get_db
from common.db.models.user import User
from features.functional.schemas.brd_stories import (
    AcceptBrdStoriesRequest,
    AcceptBrdStoriesResponse,
    GenerateStoriesFromBrdRequest,
    GenerateStoriesFromBrdResponse,
    SuggestedStory,
)
from features.functional.services.brd_story_generation_service import BrdStoryGenerationService

router = APIRouter()


@router.post(
    "/generate-stories",
    response_model=GenerateStoriesFromBrdResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate user stories from a BRD document (two-pass LLM pipeline)",
)
async def generate_stories_from_brd(
    body: GenerateStoriesFromBrdRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pass 1: LLM extracts functional modules from the BRD.
    Pass 2: LLM expands each module into user stories with full acceptance criteria.

    Returns a preview list — stories are NOT saved until accept-stories is called.
    """
    svc = BrdStoryGenerationService(db)
    modules_count, stories = await svc.generate(
        project_id=body.project_id,
        requirement_id=body.requirement_id,
        max_stories=body.max_stories,
        include_ui_context=body.include_ui_context,
    )
    return GenerateStoriesFromBrdResponse(
        requirement_id=body.requirement_id,
        modules_identified=modules_count,
        stories=stories,
        total_stories=len(stories),
    )


@router.post(
    "/accept-stories",
    response_model=AcceptBrdStoriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Accept and persist selected (or all) BRD-generated user stories",
)
async def accept_brd_stories(
    body: AcceptBrdStoriesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persists stories to the user_stories table with source='brd_generated'.

    Send the full stories list from the preview response.
    Pass indices to accept specific stories, or omit indices to accept all.
    """
    if not body.stories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stories provided. Pass the stories array from the generate-stories response.",
        )
    svc = BrdStoryGenerationService(db)
    created, story_ids, errors = await svc.accept_stories(
        project_id=body.project_id,
        suggested=body.stories,
        indices=body.indices,
    )
    return AcceptBrdStoriesResponse(
        created=created,
        story_ids=story_ids,
        errors=errors,
    )
