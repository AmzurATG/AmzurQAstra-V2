"""
Test Runs Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from features.functional.schemas.test_run import (
    TestRunCreate,
    TestRunRunAllCreate,
    TestRunStartResponse,
    TestRunResponse,
    TestRunDetailResponse,
    TestRunSummaryResponse,
    TestResultResponse,
    LiveProgressResponse,
    LogEntry,
    CompletedCaseResult,
    ActiveLaneInfo,
    GroupProgressInfo,
)
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_result import TestResultStatus
from features.functional.services.test_execution_service import (
    TestExecutionService,
)
from features.functional.orchestration.orchestrated_run_service import (
    OrchestratedRunService,
)
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.services.completed_result_builder import (
    completed_case_dict_from_orm,
    completed_case_to_lite,
    live_progress_to_lite,
)
from features.functional.services.test_run_report_service import build_report_data
from features.functional.services.test_run_pdf import build_test_run_pdf

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


@router.post("/run-all", response_model=TestRunStartResponse, status_code=status.HTTP_201_CREATED)
async def run_all_test_cases(
    run_data: TestRunRunAllCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload-ready Run All: LangGraph orchestrator + 6 local browser lanes."""
    service = OrchestratedRunService(db)
    try:
        run = await service.create_run_all(
            project_id=run_data.project_id,
            triggered_by=current_user.id,
            app_url=run_data.app_url,
            username=run_data.credentials.username if run_data.credentials else None,
            password=run_data.credentials.password if run_data.credentials else None,
            use_google_signin=run_data.use_google_signin,
            headless=run_data.headless,
            test_case_ids=run_data.test_case_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    await service.start_orchestrated_run(run.id)
    return TestRunStartResponse(run_id=run.id, status="running")


@router.post("/{run_id}/resume", response_model=TestRunStartResponse)
async def resume_orchestrated_run(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume an orchestrated run from LangGraph Postgres checkpoint."""
    service = OrchestratedRunService(db)
    try:
        await service.resume_run(run_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return TestRunStartResponse(run_id=run_id, status="running")


@router.post("/", response_model=TestRunStartResponse, status_code=status.HTTP_201_CREATED)
async def create_and_execute_test_run(
    run_data: TestRunCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test run and immediately start execution in the background."""
    service = TestExecutionService(db)
    try:
        run = await service.create_run(run_data, triggered_by=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
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
    run_number_row = (
        await db.execute(select(TestRun.run_number).where(TestRun.id == run_id))
    ).scalar_one_or_none()

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
            "active_lanes": list(progress.get("active_lanes") or []),
            "groups": list(progress.get("groups") or []),
            "live_screenshots": list(progress.get("live_screenshots") or []),
        }
        if lite:
            body = live_progress_to_lite(body)
        return LiveProgressResponse(
            run_id=run_id,
            run_number=run_number_row,
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
            active_lanes=[ActiveLaneInfo(**ln) for ln in body.get("active_lanes") or []],
            groups=[GroupProgressInfo(**g) for g in body.get("groups") or []],
            live_screenshots=body.get("live_screenshots") or [],
        )

    # Fallback: load from DB
    service = TestExecutionService(db)
    run = await service.get_run_with_results(run_id)
    if not run:
        return LiveProgressResponse(
            run_id=run_id, run_number=run_number_row, status="not_found"
        )

    pct = 100 if run.status in (
        TestRunStatus.PASSED,
        TestRunStatus.FAILED,
        TestRunStatus.ERROR,
        TestRunStatus.CANCELLED,
    ) else 0
    completed_raw = []
    for r in (run.test_results or []):
        if r.status != TestResultStatus.SKIPPED:
            d = completed_case_dict_from_orm(r)
            if lite:
                d = completed_case_to_lite(d)
            completed_raw.append(CompletedCaseResult(**d))

    return LiveProgressResponse(
        run_id=run_id,
        run_number=run.run_number,
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
    run_row = (
        await db.execute(select(TestRun).where(TestRun.id == run_id))
    ).scalar_one_or_none()
    if run_row and (run_row.config or {}).get("orchestration") == "langgraph":
        service = OrchestratedRunService(db)
        run = await service.cancel_run(run_id)
    else:
        service = TestExecutionService(db)
        run = await service.cancel_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")
    return run


@router.get("/{run_id}/report")
async def get_test_run_report(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Structured run report (summary + groups + per-case steps/adaptations) for the in-app report page."""
    report = await build_report_data(db, run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Test run not found")
    return report


@router.get("/{run_id}/report.pdf")
async def get_test_run_report_pdf(
    run_id: int,
    download: bool = Query(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloadable PDF report with embedded screenshots."""
    from fastapi import Response
    from urllib.parse import quote

    report = await build_report_data(db, run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Test run not found")
    data = build_test_run_pdf(report)
    filename = f"test-run-{report.get('run_number') or run_id}-report.pdf"
    disp = "attachment" if download else "inline"
    cd = f"{disp}; filename*=UTF-8''{quote(filename)}"
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": cd})


@router.post("/{run_id}/report/email", status_code=status.HTTP_200_OK)
async def email_test_run_report(
    run_id: int,
    body: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Email the PDF report (with screenshots attached best-effort)."""
    import asyncio
    from pathlib import Path
    from config import settings
    from common.services.smtp_mailer import (
        is_smtp_configured,
        send_email_with_pdf_attachment,
        SmtpSendError,
    )

    to_addr = (body or {}).get("to")
    if not to_addr:
        raise HTTPException(status_code=400, detail="Recipient 'to' is required")
    if not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS).",
        )
    report = await build_report_data(db, run_id)
    if not report:
        raise HTTPException(status_code=404, detail="Test run not found")
    data = build_test_run_pdf(report)
    filename = f"test-run-{report.get('run_number') or run_id}-report.pdf"

    totals = report.get("totals", {})
    subject = (
        f"{settings.APP_NAME} — Test Run #{report.get('run_number') or run_id} report "
        f"({totals.get('passed', 0)}/{totals.get('total', 0)} passed)"
    )
    text_body = (
        f"Test Run #{report.get('run_number') or run_id}\n"
        f"Status: {report.get('status')}\n"
        f"Passed {totals.get('passed', 0)} / {totals.get('total', 0)} "
        f"(success {totals.get('success_rate', 0)}%), failed {totals.get('failed', 0)}.\n"
        f"AI adaptations: {totals.get('adaptations', 0)}.\n"
    )
    html_body = f"<p>{text_body.replace(chr(10), '<br>')}</p>"

    screenshots_dir = Path(settings.SCREENSHOTS_DIR)
    attachments: list[tuple[bytes, str]] = []
    for c in report.get("failed_cases", [])[:20]:
        sp = c.get("screenshot_path")
        if not sp:
            continue
        try:
            fp = screenshots_dir / Path(str(sp)).name
            if fp.is_file():
                attachments.append((fp.read_bytes(), fp.name))
        except Exception:
            pass

    try:
        await asyncio.to_thread(
            send_email_with_pdf_attachment,
            to_addr=str(to_addr),
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            pdf_bytes=data,
            attachment_filename=filename,
            screenshot_attachments=attachments or None,
        )
    except SmtpSendError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    return {"detail": "Report email sent"}


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
