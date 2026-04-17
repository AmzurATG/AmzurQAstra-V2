"""Generate test cases from user stories (LLM)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common.db.database import get_db
from common.db.models.user import User
from common.db.models.user_story import UserStory
from common.api.deps import get_current_active_user
from features.functional.services.test_case_generation_service import TestCaseGenerationService
from api.v1.functional.user_story_schemas import (
    GenerateTestsRequest,
    GenerateTestsResponse,
    GeneratedTestCaseInfo,
)

router = APIRouter()


@router.post(
    "/{project_id}/{user_story_id}/generate-tests",
    response_model=GenerateTestsResponse,
    summary="Generate test cases from a user story",
)
async def generate_tests_from_user_story(
    project_id: int,
    user_story_id: int,
    request: GenerateTestsRequest = GenerateTestsRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == user_story_id,
            UserStory.project_id == project_id,
        )
    )
    user_story = result.scalar_one_or_none()

    if not user_story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found",
        )

    service = TestCaseGenerationService(db)
    result = await service.generate_test_cases_from_user_story(
        user_story_id=user_story_id,
        include_steps=request.include_steps,
        force_regenerate=request.force_regenerate,
    )

    if result.get("code") == "already_exists":
        return GenerateTestsResponse(
            success=False,
            user_story_id=user_story_id,
            user_story_key=result.get("user_story_key"),
            test_cases_created=0,
            test_cases=[],
            error=result.get("error"),
            code="already_exists",
        )

    if not result.get("success"):
        err_code = str(result.get("error_code") or "").lower()
        detail = result.get("error", "Failed to generate test cases")
        if err_code == "invalid_llm_output":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=detail,
            )
        low = str(detail).lower()
        if any(k in low for k in ("timeout", "temporar", "rate limit", "connection", "unavailable")):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )

    return GenerateTestsResponse(
        success=True,
        user_story_id=user_story_id,
        user_story_key=result.get("user_story_key"),
        test_cases_created=result.get("test_cases_created", 0),
        test_cases=[
            GeneratedTestCaseInfo(**tc) for tc in result.get("test_cases", [])
        ],
        error=None,
        code=result.get("code"),
    )
