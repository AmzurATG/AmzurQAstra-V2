"""
Test Steps Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from features.functional.schemas.test_step import (
    TestStepCreate,
    TestStepUpdate,
    TestStepResponse,
    TestStepReorder,
)
from features.functional.services.test_case_service import TestCaseService


router = APIRouter()


@router.get("/{test_case_id}", response_model=List[TestStepResponse])
async def list_test_steps(
    test_case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List test steps for a test case."""
    service = TestCaseService(db)
    steps = await service.get_steps(test_case_id)
    return steps


@router.post("/", response_model=TestStepResponse, status_code=status.HTTP_201_CREATED)
async def create_test_step(
    step_data: TestStepCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new test step."""
    service = TestCaseService(db)
    step = await service.add_step(step_data)
    return step


@router.put("/{step_id}", response_model=TestStepResponse)
async def update_test_step(
    step_id: int,
    step_data: TestStepUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a test step."""
    service = TestCaseService(db)
    step = await service.update_step(step_id, step_data)
    
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test step not found",
        )
    
    return step


@router.delete("/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_step(
    step_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a test step."""
    service = TestCaseService(db)
    deleted = await service.delete_step(step_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test step not found",
        )


@router.post("/reorder", response_model=List[TestStepResponse])
async def reorder_test_steps(
    reorder_data: TestStepReorder,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder test steps."""
    service = TestCaseService(db)
    steps = await service.reorder_steps(
        test_case_id=reorder_data.test_case_id,
        step_ids=reorder_data.step_ids,
    )
    return steps
