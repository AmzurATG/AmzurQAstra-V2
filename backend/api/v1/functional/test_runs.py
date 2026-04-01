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
    TestRunStartResponse,
    TestRunResponse,
    TestRunDetailResponse,
    TestResultResponse,
    LiveProgressResponse,
    LogEntry,
    CompletedCaseResult,
)
from features.functional.db.models.test_run import TestRunStatus
from features.functional.db.models.test_result import TestResultStatus
from features.functional.services.test_execution_service import (
    TestExecutionService,
)
from features.functional.services.run_progress_manager import RunProgressManager

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[TestRunResponse])
async def list_test_runs(
    project_id: int,
    status_filter: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = TestExecutionService(db)
    runs, total = await service.get_runs(project_id, status_filter, pagination)
    return PaginatedResponse.create(
        items=runs, total=total,
        page=pagination.page, page_size=pagination.page_size,
    )


@router.post("/", response_model=TestRunStartResponse, status_code=status.HTTP_201_CREATED)
async def create_and_execute_test_run(
    run_data: TestRunCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test run and immediately start execution in the background."""
    service = TestExecutionService(db)
    run = await service.create_run(run_data, triggered_by=current_user.id)
    await service.start_execution(run.id, run_data)
    return TestRunStartResponse(run_id=run.id, status="running")


@router.get("/{run_id}", response_model=TestRunDetailResponse)
async def get_test_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = TestExecutionService(db)
    run = await service.get_run_with_results(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return run


@router.get("/{run_id}/live", response_model=LiveProgressResponse)
async def get_live_progress(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll live execution progress. Falls back to DB for completed runs."""
    progress_manager = RunProgressManager()
    progress = progress_manager.get(run_id)
    if progress:
        return LiveProgressResponse(
            run_id=run_id,
            status=progress.get("status", "running"),
            percentage=progress.get("percentage", 0),
            current_test_case_index=progress.get("current_test_case_index", 0),
            total_test_cases=progress.get("total_test_cases", 0),
            current_test_case_title=progress.get("current_test_case_title"),
            current_step_info=progress.get("current_step_info"),
            completed_results=[
                CompletedCaseResult(**r) for r in progress.get("completed_results", [])
            ],
            logs=[LogEntry(**l) for l in progress.get("logs", [])],
            error=progress.get("error"),
        )

    # Fallback: load from DB
    service = TestExecutionService(db)
    run = await service.get_run_with_results(run_id)
    if not run:
        return LiveProgressResponse(run_id=run_id, status="not_found")

    pct = 100 if run.status in (TestRunStatus.PASSED, TestRunStatus.FAILED, TestRunStatus.ERROR) else 0
    completed = []
    for r in (run.test_results or []):
        if r.status != TestResultStatus.SKIPPED:
            completed.append(CompletedCaseResult(
                test_case_id=r.test_case_id,
                title=f"Test Case #{r.test_case_id}",
                status=r.status.value,
                steps_total=len(r.step_results) if r.step_results else 0,
                steps_passed=sum(1 for s in (r.step_results or []) if s.get("status") == "passed"),
                steps_failed=sum(1 for s in (r.step_results or []) if s.get("status") != "passed"),
                duration_ms=r.duration_ms or 0,
                step_results=r.step_results,
                adapted_steps=r.adapted_steps,
                original_steps=r.original_steps,
            ))

    return LiveProgressResponse(
        run_id=run_id,
        status=run.status.value,
        percentage=pct,
        total_test_cases=run.total_tests,
        current_test_case_index=run.total_tests if pct == 100 else 0,
        completed_results=completed,
    )


@router.post("/{run_id}/cancel", response_model=TestRunResponse)
async def cancel_test_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = TestExecutionService(db)
    run = await service.cancel_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return run


@router.get("/{run_id}/results", response_model=List[TestResultResponse])
async def get_test_run_results(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = TestExecutionService(db)
    return await service.get_results(run_id)


@router.post("/results/{result_id}/steps/{step_number}/sync", response_model=dict)
async def sync_adapted_step(
    result_id: int,
    step_number: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync an AI-adapted step back to the original test case."""
    service = TestExecutionService(db)
    success = await service.sync_adapted_step(result_id, step_number)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to sync step. Adaptation not found or invalid.")
    return {"success": True}


@router.get("/{run_id}/results/{result_id}/screenshot")
async def get_test_result_screenshot(
    run_id: int,
    result_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import FileResponse
    service = TestExecutionService(db)
    path = await service.get_screenshot_path(result_id)
    if not path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path)
