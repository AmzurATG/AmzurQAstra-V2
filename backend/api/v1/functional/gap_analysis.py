"""
Gap analysis API: BRD vs user stories.
"""
import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from common.api.deps import get_current_active_user
from common.api.pagination import PaginatedResponse, PaginationParams
from common.db.models.user import User
from common.db.database import get_db
from common.schemas.report_email import SendReportEmailRequest
from common.services.report_email_enrichment import rich_parts_for_gap_analysis
from common.services.smtp_mailer import (
    SmtpSendError,
    build_report_email_envelope,
    is_smtp_configured,
    send_email_with_pdf_attachment,
)
from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.schemas.gap_analysis import (
    AcceptGapSuggestionsRequest,
    GapAnalysisRunCreate,
    GapAnalysisRunResponse,
)
from features.functional.db.models.gap_analysis_run import GapAnalysisRun
from features.functional.services.gap_analysis_service import GapAnalysisService


router = APIRouter()


def _run_to_response(run: GapAnalysisRun) -> GapAnalysisRunResponse:
    req = run.requirement
    return GapAnalysisRunResponse(
        id=run.id,
        project_id=run.project_id,
        requirement_id=run.requirement_id,
        created_by=run.created_by,
        status=run.status,
        result_json=run.result_json,
        error_message=run.error_message,
        pdf_path=run.pdf_path,
        requirement_title=req.title if req else None,
        requirement_file_name=req.file_name if req else None,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/runs", response_model=GapAnalysisRunResponse, status_code=status.HTTP_201_CREATED)
async def create_gap_analysis_run(
    data: GapAnalysisRunCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GapAnalysisService(db)
    run = await svc.run_analysis(data.project_id, data.requirement_id, current_user.id)
    return _run_to_response(run)


@router.get("/runs", response_model=PaginatedResponse[GapAnalysisRunResponse])
async def list_gap_analysis_runs(
    project_id: int = Query(..., description="Project id"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GapAnalysisService(db)
    items, total = await svc.list_runs(
        project_id, pagination.offset, pagination.page_size
    )
    responses = [
        GapAnalysisRunResponse(
            id=i["id"],
            project_id=i["project_id"],
            requirement_id=i["requirement_id"],
            created_by=i["created_by"],
            status=i["status"],
            result_json=i["result_json"],
            error_message=i["error_message"],
            pdf_path=i["pdf_path"],
            requirement_title=i.get("requirement_title"),
            requirement_file_name=i.get("requirement_file_name"),
            created_at=i["created_at"],
            updated_at=i["updated_at"],
        )
        for i in items
    ]
    return PaginatedResponse.create(
        items=responses,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/runs/{run_id}", response_model=GapAnalysisRunResponse)
async def get_gap_analysis_run(
    run_id: int,
    project_id: int = Query(..., description="Project id (scope)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GapAnalysisService(db)
    run = await svc.get_run(run_id, project_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return _run_to_response(run)


@router.get("/runs/{run_id}/pdf")
async def download_gap_analysis_pdf(
    run_id: int,
    project_id: int = Query(..., description="Project id"),
    download: bool = Query(False, description="If true, use attachment disposition"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GapAnalysisService(db)
    data, filename = await svc.get_pdf_bytes(run_id, project_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this run",
        )
    disp = "attachment" if download else "inline"
    cd = f'{disp}; filename*=UTF-8\'\'{quote(filename)}'
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": cd})


@router.post("/runs/{run_id}/email", status_code=status.HTTP_200_OK)
async def email_gap_analysis_pdf(
    run_id: int,
    body: SendReportEmailRequest,
    project_id: int = Query(..., description="Project id"),
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
    svc = GapAnalysisService(db)
    run = await svc.get_run(run_id, project_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    data, filename = await svc.get_pdf_bytes(run_id, project_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this run",
        )
    req = run.requirement
    rich = rich_parts_for_gap_analysis(
        run.result_json if isinstance(run.result_json, dict) else None
    )
    subject, text_body, html_body = build_report_email_envelope(
        report_title_phrase="Requirements gap analysis",
        requirement_title=req.title if req else None,
        requirement_file_name=req.file_name if req else None,
        requirement_id=run.requirement_id,
        run_id=run.id,
        run_created_at=run.created_at,
        rich=rich,
    )
    try:
        await asyncio.to_thread(
            send_email_with_pdf_attachment,
            to_addr=str(body.to),
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            pdf_bytes=data,
            attachment_filename=filename or "gap-analysis-report.pdf",
        )
    except SmtpSendError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=e.message,
        ) from e
    return {"detail": "Report email sent"}


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gap_analysis_run(
    run_id: int,
    project_id: int = Query(..., description="Project id"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GapAnalysisService(db)
    ok = await svc.delete_run(run_id, project_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/runs/{run_id}/accept-suggestions")
async def accept_gap_suggestions(
    run_id: int,
    body: AcceptGapSuggestionsRequest,
    project_id: int = Query(..., description="Project id"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    svc = GapAnalysisService(db)
    created, errors = await svc.accept_suggestions(run_id, project_id, body.indices)
    return {"created": created, "errors": errors}
