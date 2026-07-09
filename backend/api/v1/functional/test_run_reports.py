"""
Test Run Report Endpoints

POST   /functional/test-runs/{run_id}/report/generate   — kick off background PDF generation
GET    /functional/test-runs/{run_id}/report/status     — poll generation progress
GET    /functional/test-runs/{run_id}/report/download   — stream the generated PDF
POST   /functional/test-runs/{run_id}/report/email      — email the PDF to a recipient
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.api.deps import get_current_active_user
from common.db.database import get_db
from common.db.models.user import User
from common.services.smtp_mailer import SmtpSendError, is_smtp_configured
from features.functional.db.models.test_run import TestRun
from features.functional.services.test_run_report_service import (
    TestRunReportService,
    _pdf_storage_path,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportGenerateResponse(BaseModel):
    run_id: int
    status: str
    message: str


class ReportStatusResponse(BaseModel):
    run_id: int
    status: str          # not_started | generating | ready | failed | not_found
    error: str | None = None


class ReportEmailRequest(BaseModel):
    to: EmailStr


class ReportEmailResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{run_id}/report/generate",
    response_model=ReportGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kick off background PDF report generation for a test run",
)
async def generate_report(
    run_id: int,
    force: bool = False,
    format: str = "short",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ReportGenerateResponse:
    """
    Start asynchronous PDF report generation for ``run_id``.

    ``format``: ``short`` (default — cover, index, failures) or ``long`` (full evidence).
    Returns immediately (202) with a status of ``generating`` or ``ready``.
    """
    svc = TestRunReportService(db)
    result = await svc.generate(run_id, force=force, report_format=format)
    return ReportGenerateResponse(**result)


@router.get(
    "/{run_id}/report/status",
    response_model=ReportStatusResponse,
    summary="Poll background report generation status",
)
async def report_status(
    run_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ReportStatusResponse:
    """
    Returns ``status``:
    - ``not_started`` — never triggered
    - ``generating``  — background task running
    - ``ready``       — PDF available for download
    - ``failed``      — generation error (see ``error`` field)
    - ``not_found``   — run id does not exist
    """
    svc = TestRunReportService(db)
    info = await svc.get_status(run_id)
    return ReportStatusResponse(
        run_id=run_id,
        status=info["status"],
        error=info.get("error"),
    )


@router.get(
    "/{run_id}/report/download",
    summary="Download the generated PDF report",
)
async def download_report(
    run_id: int,
    format: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream the generated PDF as a file download.

    Optional ``format=short|long`` prefers that file when both exist.
    """
    svc = TestRunReportService(db)
    pdf_path = await svc.get_pdf_path(run_id)
    if format in ("short", "long"):
        project_id = (
            await db.execute(select(TestRun.project_id).where(TestRun.id == run_id))
        ).scalar_one_or_none()
        if project_id is not None:
            candidate = _pdf_storage_path(int(project_id), run_id, format)
            if candidate.exists():
                pdf_path = str(candidate)
    if not pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not ready. Call POST /report/generate first and wait for status 'ready'.",
        )
    fmt_tag = f"_{format}" if format in ("short", "long") else ""
    filename = f"QAstra_TestRun_{run_id}{fmt_tag}_Report.pdf"
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{run_id}/report/email",
    response_model=ReportEmailResponse,
    summary="Email the generated PDF report to a recipient",
)
async def email_report(
    run_id: int,
    body: ReportEmailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ReportEmailResponse:
    """
    Send the generated PDF as an email attachment to ``to``.

    SMTP must be configured via environment variables. Returns 400 if the
    report is not ready or 503 if SMTP is not configured.
    """
    if not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured on this server. Set SMTP_HOST and EMAIL_FROM_ADDRESS.",
        )

    svc = TestRunReportService(db)

    # Verify report is ready before attempting email
    info = await svc.get_status(run_id)
    if info["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready (status: {info['status']}). Generate it first.",
        )

    try:
        await svc.send_email(run_id, body.to)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SmtpSendError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message)

    return ReportEmailResponse(detail=f"Report emailed successfully to {body.to}")
