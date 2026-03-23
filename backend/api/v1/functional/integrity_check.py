"""
Integrity Check Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from common.db.database import get_db
from common.db.models.user import User
from common.db.models.user_story import UserStory
from common.api.deps import get_current_active_user
from features.functional.schemas.integrity_check import (
    IntegrityCheckRequest,
    IntegrityCheckResponse,
)
from features.functional.services.integrity_check_service import IntegrityCheckService
from features.functional.db.models.test_case import TestCase


router = APIRouter()


# =====================================================
# PREVIEW SCHEMAS
# =====================================================

class PreviewStepResponse(BaseModel):
    step_number: int
    action: str
    target: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    expected_result: Optional[str] = None


class PreviewTestCaseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    integrity_check: bool = False
    steps: List[PreviewStepResponse] = []


class PreviewUserStoryResponse(BaseModel):
    id: int
    title: str
    external_key: Optional[str] = None
    status: str
    priority: str
    item_type: str
    integrity_check: bool = False
    test_cases: List[PreviewTestCaseResponse] = []


class IntegrityCheckPreviewResponse(BaseModel):
    user_stories: List[PreviewUserStoryResponse] = []
    standalone_test_cases: List[PreviewTestCaseResponse] = []
    total_user_stories: int = 0
    total_test_cases: int = 0
    total_steps: int = 0


# =====================================================
# ENDPOINTS
# =====================================================

@router.get("/preview/{project_id}", response_model=IntegrityCheckPreviewResponse)
async def get_integrity_check_preview(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview what will be executed during an integrity check.

    Returns user stories, test cases, and test steps that are
    flagged for integrity check — without actually running anything.
    """
    # Get user stories flagged for integrity check
    us_query = (
        select(UserStory)
        .where(UserStory.project_id == project_id)
        .where(UserStory.integrity_check == True)
        .order_by(UserStory.id)
    )
    us_result = await db.execute(us_query)
    flagged_user_stories = list(us_result.scalars().all())
    flagged_us_ids = [us.id for us in flagged_user_stories]

    # Get test cases: directly flagged OR belonging to flagged user stories
    conditions = [TestCase.integrity_check == True]
    if flagged_us_ids:
        conditions.append(TestCase.user_story_id.in_(flagged_us_ids))

    tc_query = (
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.project_id == project_id)
        .where(or_(*conditions))
        .order_by(TestCase.id)
    )
    tc_result = await db.execute(tc_query)
    all_test_cases = list(tc_result.scalars().all())

    # Group test cases by user story
    us_test_cases: dict[int, list] = {}
    standalone_test_cases: list = []

    for tc in all_test_cases:
        if tc.user_story_id and tc.user_story_id in flagged_us_ids:
            us_test_cases.setdefault(tc.user_story_id, []).append(tc)
        else:
            standalone_test_cases.append(tc)

    def build_step(step):
        return PreviewStepResponse(
            step_number=step.step_number,
            action=step.action.value if hasattr(step.action, 'value') else str(step.action),
            target=step.target,
            value=step.value,
            description=step.description,
            expected_result=step.expected_result,
        )

    def build_tc(tc):
        steps = sorted(tc.steps, key=lambda s: s.step_number)
        return PreviewTestCaseResponse(
            id=tc.id,
            title=tc.title,
            description=tc.description,
            priority=tc.priority.value if hasattr(tc.priority, 'value') else str(tc.priority) if tc.priority else None,
            integrity_check=tc.integrity_check or False,
            steps=[build_step(s) for s in steps],
        )

    # Build user story responses
    user_story_responses = []
    for us in flagged_user_stories:
        tcs = us_test_cases.get(us.id, [])
        user_story_responses.append(PreviewUserStoryResponse(
            id=us.id,
            title=us.title,
            external_key=us.external_key,
            status=us.status.value if hasattr(us.status, 'value') else str(us.status),
            priority=us.priority.value if hasattr(us.priority, 'value') else str(us.priority),
            item_type=us.item_type.value if hasattr(us.item_type, 'value') else str(us.item_type),
            integrity_check=us.integrity_check,
            test_cases=[build_tc(tc) for tc in tcs],
        ))

    standalone_responses = [build_tc(tc) for tc in standalone_test_cases]

    total_tcs = len(all_test_cases)
    total_steps = sum(len(tc.steps) for tc in all_test_cases)

    return IntegrityCheckPreviewResponse(
        user_stories=user_story_responses,
        standalone_test_cases=standalone_responses,
        total_user_stories=len(flagged_user_stories),
        total_test_cases=total_tcs,
        total_steps=total_steps,
    )


@router.post("/", response_model=IntegrityCheckResponse)
async def run_integrity_check(
    request: IntegrityCheckRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run build integrity check on an application.
    
    This verifies:
    - App is reachable
    - Login works with provided credentials
    - Critical pages/endpoints are accessible
    - Basic UI elements are present
    """
    service = IntegrityCheckService(db)
    result = await service.run_check(request)
    return result


@router.get("/history/{project_id}", response_model=list)
async def get_integrity_check_history(
    project_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get integrity check history for a project."""
    service = IntegrityCheckService(db)
    history = await service.get_history(project_id, limit)
    return history
