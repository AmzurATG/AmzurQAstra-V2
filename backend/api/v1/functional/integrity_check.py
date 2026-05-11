"""
Integrity Check Endpoints
POST  /run             — start async check, return run_id
GET   /{run_id}/status — poll live progress
GET   /{run_id}/pdf    — download report PDF (terminal runs only)
POST  /{run_id}/email  — email report PDF
GET   /preview/{pid}   — preview flagged test cases (unchanged)
GET   /history/{pid}   — past runs
"""
import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from common.db.database import get_db
from common.db.models.user import User
from common.db.models.user_story import UserStory
from common.api.deps import get_current_active_user
from common.schemas.report_email import SendReportEmailRequest
from common.services.smtp_mailer import (
    SmtpSendError,
    build_integrity_check_report_email_envelope,
    is_smtp_configured,
    send_email_with_pdf_attachment,
)
from features.functional.schemas.integrity_check import (
    IntegrityCheckRequest,
    RunStartResponse,
    RunStatusResponse,
    IntegrityCheckPreviewResponse,
    PreviewStepResponse,
    PreviewTestCaseResponse,
    PreviewUserStoryResponse,
)
from features.functional.services.integrity_check_service import IntegrityCheckService
from features.functional.db.models.test_case import TestCase

router = APIRouter()


# ── Start run ─────────────────────────────────────────────────────────────────

@router.post("/run", response_model=RunStartResponse)
async def start_integrity_check(
    request: IntegrityCheckRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start an async integrity check.
    Returns run_id immediately; poll /{run_id}/status for live progress.
    """
    service = IntegrityCheckService(db)
    return await service.start_check(request, request.project_id)


# ── Poll status ───────────────────────────────────────────────────────────────

@router.get("/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll live progress or fetch historical result for a given run_id."""
    service = IntegrityCheckService(db)
    return await service.get_run_status(run_id)


@router.get("/{run_id}/pdf")
async def download_integrity_check_pdf(
    run_id: str,
    project_id: int = Query(..., description="Project id (scope)"),
    download: bool = Query(False, description="If true, use attachment disposition"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = IntegrityCheckService(db)
    record = await service.get_run_record(run_id, project_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if record.status not in ("completed", "error"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is not ready yet. Wait until the run finishes.",
        )
    data, filename = await service.get_pdf_bytes(run_id, project_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF could not be generated for this run",
        )
    disp = "attachment" if download else "inline"
    cd = f'{disp}; filename*=UTF-8\'\'{quote(filename or "bic-report.pdf")}'
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": cd})


@router.post("/{run_id}/email", status_code=status.HTTP_200_OK)
async def email_integrity_check_pdf(
    run_id: str,
    body: SendReportEmailRequest,
    project_id: int = Query(..., description="Project id (scope)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Email delivery is not configured on the server. "
                "Set SMTP_HOST and EMAIL_FROM_ADDRESS (see .env.example)."
            ),
        )
    service = IntegrityCheckService(db)
    record = await service.get_run_record(run_id, project_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if record.status not in ("completed", "error"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is not ready yet. Wait until the run finishes.",
        )
    data, filename = await service.get_pdf_bytes(run_id, project_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this run",
        )
    subject, text_body, html_body = build_integrity_check_report_email_envelope(
        run_id=record.run_id,
        project_id=project_id,
        app_url=record.app_url,
        run_completed_at=record.completed_at,
    )
    try:
        await asyncio.to_thread(
            send_email_with_pdf_attachment,
            to_addr=str(body.to),
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            pdf_bytes=data,
            attachment_filename=filename or "bic-report.pdf",
        )
    except SmtpSendError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message,
        ) from e
    return {"detail": "Report email sent"}


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history/{project_id}", response_model=list)
async def get_integrity_check_history(
    project_id: int,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get past integrity check runs for a project."""
    service = IntegrityCheckService(db)
    return await service.get_history(project_id, limit)


# ── Preview ───────────────────────────────────────────────────────────────────

@router.get("/preview/{project_id}", response_model=IntegrityCheckPreviewResponse)
async def get_integrity_check_preview(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview test cases flagged for integrity check without running them."""
    us_query = (
        select(UserStory)
        .where(UserStory.project_id == project_id)
        .where(UserStory.integrity_check == True)
        .order_by(UserStory.id)
    )
    us_result = await db.execute(us_query)
    flagged_us = list(us_result.scalars().all())
    flagged_us_ids = [us.id for us in flagged_us]

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
    all_tcs = list(tc_result.scalars().all())

    us_tc_map: dict[int, list] = {}
    standalone: list = []
    for tc in all_tcs:
        if tc.user_story_id and tc.user_story_id in flagged_us_ids:
            us_tc_map.setdefault(tc.user_story_id, []).append(tc)
        else:
            standalone.append(tc)

    def _step(s) -> PreviewStepResponse:
        return PreviewStepResponse(
            step_number=s.step_number,
            action=s.action.value if hasattr(s.action, "value") else str(s.action),
            target=s.target,
            value=s.value,
            description=s.description,
            expected_result=s.expected_result,
        )

    def _tc(tc) -> PreviewTestCaseResponse:
        steps = sorted(tc.steps, key=lambda s: s.step_number)
        priority = tc.priority.value if hasattr(tc.priority, "value") else str(tc.priority) if tc.priority else None
        return PreviewTestCaseResponse(
            id=tc.id,
            case_number=getattr(tc, "case_number", 0) or 0,
            title=tc.title,
            description=tc.description,
            priority=priority, integrity_check=tc.integrity_check or False,
            steps=[_step(s) for s in steps],
        )

    us_responses = [
        PreviewUserStoryResponse(
            id=us.id, title=us.title, external_key=us.external_key,
            status=us.status.value if hasattr(us.status, "value") else str(us.status),
            priority=us.priority.value if hasattr(us.priority, "value") else str(us.priority),
            item_type=us.item_type.value if hasattr(us.item_type, "value") else str(us.item_type),
            integrity_check=us.integrity_check,
            test_cases=[_tc(tc) for tc in us_tc_map.get(us.id, [])],
        )
        for us in flagged_us
    ]

    return IntegrityCheckPreviewResponse(
        user_stories=us_responses,
        standalone_test_cases=[_tc(tc) for tc in standalone],
        total_user_stories=len(flagged_us),
        total_test_cases=len(all_tcs),
        total_steps=sum(len(tc.steps) for tc in all_tcs),
    )
