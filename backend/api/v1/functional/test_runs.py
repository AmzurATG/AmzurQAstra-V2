"""
Test Runs Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from features.functional.schemas.test_run import (
    TestRunCreate,
    TestRunResponse,
    TestRunDetailResponse,
    TestResultResponse,
)
from features.functional.services.test_execution_service import TestExecutionService


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[TestRunResponse])
async def list_test_runs(
    project_id: int,
    status: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List test runs for a project."""
    service = TestExecutionService(db)
    runs, total = await service.get_runs(project_id, status, pagination)
    
    return PaginatedResponse.create(
        items=runs,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/", response_model=TestRunResponse, status_code=status.HTTP_201_CREATED)
async def create_test_run(
    run_data: TestRunCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and start a test run."""
    service = TestExecutionService(db)
    run = await service.create_run(run_data, triggered_by=current_user.id)
    return run


@router.get("/{run_id}", response_model=TestRunDetailResponse)
async def get_test_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get test run details with results."""
    service = TestExecutionService(db)
    run = await service.get_run_with_results(run_id)
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found",
        )
    
    return run


@router.post("/{run_id}/execute", response_model=TestRunResponse)
async def execute_test_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a pending test run."""
    service = TestExecutionService(db)
    run = await service.execute_run(run_id)
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found",
        )
    
    return run


@router.post("/{run_id}/cancel", response_model=TestRunResponse)
async def cancel_test_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running test run."""
    service = TestExecutionService(db)
    run = await service.cancel_run(run_id)
    
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test run not found",
        )
    
    return run


@router.get("/{run_id}/results", response_model=List[TestResultResponse])
async def get_test_run_results(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all results for a test run."""
    service = TestExecutionService(db)
    results = await service.get_results(run_id)
    return results


@router.get("/{run_id}/results/{result_id}/screenshot")
async def get_test_result_screenshot(
    run_id: int,
    result_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get screenshot for a test result."""
    from fastapi.responses import FileResponse
    service = TestExecutionService(db)
    screenshot_path = await service.get_screenshot_path(result_id)
    
    if not screenshot_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not found",
        )
    
    return FileResponse(screenshot_path)
