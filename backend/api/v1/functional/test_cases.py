"""
Test Cases Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from features.functional.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    TestCaseWithSteps,
    GenerateTestCasesRequest,
)
from features.functional.services.test_case_service import TestCaseService


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[TestCaseResponse])
async def list_test_cases(
    project_id: int,
    requirement_id: Optional[int] = None,
    user_story_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List test cases with filters."""
    service = TestCaseService(db)
    test_cases, total = await service.get_list(
        project_id=project_id,
        requirement_id=requirement_id,
        user_story_id=user_story_id,
        status=status,
        priority=priority,
        category=category,
        search=search,
        pagination=pagination,
    )
    
    return PaginatedResponse.create(
        items=test_cases,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_test_case(
    test_case_data: TestCaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new test case."""
    service = TestCaseService(db)
    test_case = await service.create(test_case_data, created_by=current_user.id)
    return test_case


@router.get("/{test_case_id}", response_model=TestCaseWithSteps)
async def get_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a test case by ID with all steps."""
    service = TestCaseService(db)
    test_case = await service.get_by_id_with_steps(test_case_id)
    
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )
    
    return test_case


@router.put("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: int,
    test_case_data: TestCaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a test case."""
    service = TestCaseService(db)
    test_case = await service.update(test_case_id, test_case_data)
    
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )
    
    return test_case


@router.delete("/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a test case."""
    service = TestCaseService(db)
    deleted = await service.delete(test_case_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )


@router.post("/generate", response_model=dict)
async def generate_test_cases(
    request: GenerateTestCasesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate test cases using LLM from requirements or Jira stories."""
    from features.functional.services.test_case_generation_service import TestCaseGenerationService
    service = TestCaseGenerationService(db)
    result = await service.generate_test_cases(request)
    return result


@router.post("/{test_case_id}/generate-steps", response_model=dict)
async def generate_test_steps(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate test steps for a test case using LLM."""
    from features.functional.services.test_step_generation_service import TestStepGenerationService
    service = TestStepGenerationService(db)
    result = await service.generate_test_steps(test_case_id)
    return result


@router.post("/{test_case_id}/regenerate-steps", response_model=dict)
async def regenerate_test_steps(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate test steps for a test case (deletes existing steps first)."""
    from features.functional.services.test_step_generation_service import TestStepGenerationService
    service = TestStepGenerationService(db)
    result = await service.regenerate_test_steps(test_case_id)
    return result
