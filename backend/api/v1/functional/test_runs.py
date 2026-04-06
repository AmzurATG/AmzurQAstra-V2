"""
Test Runs Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    TestRunSummaryResponse,
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
from features.functional.services.completed_result_builder import (
    completed_case_dict_from_orm,
    completed_case_to_lite,
    live_progress_to_lite,
)

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


@router.get("/summary", response_model=TestRunSummaryResponse)
async def test_runs_summary(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate run counts for the project (all statuses)."""
    service = TestExecutionService(db)
    data = await service.get_run_summary(project_id)
    return TestRunSummaryResponse(**data)


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
    lite: bool = Query(
        True,
        description="Omit heavy fields (step_results, agent_logs, …) and trim logs for faster polling.",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll live execution progress. Falls back to DB for completed runs."""
    progress_manager = RunProgressManager()
    progress = progress_manager.get(run_id)
    if progress:
        body = {
            "status": progress.get("status", "running"),
            "percentage": progress.get("percentage", 0),
            "current_test_case_index": progress.get("current_test_case_index", 0),
            "total_test_cases": progress.get("total_test_cases", 0),
            "current_test_case_title": progress.get("current_test_case_title"),
            "current_step_info": progress.get("current_step_info"),
            "completed_results": list(progress.get("completed_results", [])),
            "logs": list(progress.get("logs", [])),
            "error": progress.get("error"),
        }
        if lite:
            body = live_progress_to_lite(body)
        return LiveProgressResponse(
            run_id=run_id,
            status=body["status"],
            percentage=body["percentage"],
            current_test_case_index=body["current_test_case_index"],
            total_test_cases=body["total_test_cases"],
            current_test_case_title=body.get("current_test_case_title"),
            current_step_info=body.get("current_step_info"),
            completed_results=[
                CompletedCaseResult(**r) for r in body["completed_results"]
            ],
            logs=[LogEntry(**l) for l in body["logs"]],
            error=body.get("error"),
        )

    # Fallback: load from DB
    service = TestExecutionService(db)
    run = await service.get_run_with_results(run_id)
    if not run:
        return LiveProgressResponse(run_id=run_id, status="not_found")

    pct = 100 if run.status in (TestRunStatus.PASSED, TestRunStatus.FAILED, TestRunStatus.ERROR) else 0
    completed_raw = []
    for r in (run.test_results or []):
        if r.status != TestResultStatus.SKIPPED:
            d = completed_case_dict_from_orm(r)
            if lite:
                d = completed_case_to_lite(d)
            completed_raw.append(CompletedCaseResult(**d))

    return LiveProgressResponse(
        run_id=run_id,
        status=run.status.value,
        percentage=pct,
        total_test_cases=run.total_tests,
        current_test_case_index=run.total_tests if pct == 100 else 0,
        completed_results=completed_raw,
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


@router.get("/{run_id}/results/{result_id}", response_model=TestResultResponse)
async def get_test_run_result(
    run_id: int,
    result_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Full test result (steps, agent_logs, …) for one case — fetch when expanding a row."""
    service = TestExecutionService(db)
    tr = await service.get_result_for_run(run_id, result_id)
    if not tr:
        raise HTTPException(status_code=404, detail="Test result not found")
    return tr


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
    file_path = await service.get_primary_screenshot_file(run_id, result_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(file_path)


@router.get("/{run_id}/results/{result_id}/screenshots/{filename}")
async def get_test_result_screenshot_file(
    run_id: int,
    result_id: int,
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Serve a screenshot file listed on agent_logs or screenshot_path (JWT required)."""
    from fastapi.responses import FileResponse

    service = TestExecutionService(db)
    file_path = await service.get_authorized_screenshot_file(run_id, result_id, filename)
    if not file_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(file_path)
