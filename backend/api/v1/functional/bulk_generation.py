"""
Bulk Test Generation API.

Two endpoints:
  POST /user-stories/{project_id}/bulk-generate-tests
      Creates a GenerationJob and fires off the background pipeline.
  GET  /user-stories/{project_id}/bulk-generate-tests/{job_id}
      Returns current job status, progress %, and coverage report when complete.
"""
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.api.deps import get_current_active_user
from common.db.database import get_db, async_session_maker
from common.db.models.user import User
from features.functional.schemas.bulk_generation import (
    BulkGenerateRequest,
    BulkGenerateResponse,
    GenerationJobStatusResponse,
)
from features.functional.services.bulk_generation_service import BulkGenerationService
from features.functional.services.generation_job_service import GenerationJobService

router = APIRouter()


async def _run_bulk_generation_task(job_id: int, include_steps: bool) -> None:
    """
    Background task entry point. Opens its own DB session so it outlives
    the request session (which is closed after the response is sent).
    """
    async with async_session_maker() as db:
        svc = BulkGenerationService(db)
        try:
            await svc.run(job_id=job_id, include_steps=include_steps)
        except Exception as exc:
            job_svc = GenerationJobService(db)
            await job_svc.mark_failed(job_id, str(exc))


@router.post(
    "/{project_id}/bulk-generate-tests",
    response_model=BulkGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start bulk test-case generation for selected user stories",
)
async def bulk_generate_tests(
    project_id: int,
    body: BulkGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a GenerationJob and immediately returns its ID.
    The frontend polls GET /{project_id}/bulk-generate-tests/{job_id} for progress.

    Profile options: light (~5/story), standard (~10/story), comprehensive (~20/story),
    production_web (comprehensive + UI inventory rows when discovery exists).
    """
    if body.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id in URL and body must match.",
        )

    valid_profiles = {"light", "standard", "comprehensive", "production_web"}
    if body.profile not in valid_profiles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile. Must be one of: {', '.join(sorted(valid_profiles))}",
        )

    job_svc = GenerationJobService(db)
    job = await job_svc.create_job(
        project_id=project_id,
        story_ids=body.story_ids,
        profile=body.profile,
        created_by=current_user.id,
    )

    background_tasks.add_task(
        _run_bulk_generation_task,
        job_id=job.id,
        include_steps=body.include_steps,
    )

    return BulkGenerateResponse(
        job_id=job.id,
        status="queued",
        total_stories=len(body.story_ids),
        message=(
            f"Bulk generation started for {len(body.story_ids)} stories "
            f"(profile: {body.profile}). Poll the status endpoint for progress."
        ),
    )


@router.get(
    "/{project_id}/bulk-generate-tests/{job_id}",
    response_model=GenerationJobStatusResponse,
    summary="Poll bulk test-case generation job status",
)
async def get_bulk_generation_status(
    project_id: int,
    job_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns live progress (0–100%) and the full coverage report on completion.

    Frontend polls every 3 seconds while status is 'queued' or 'running'.
    """
    job_svc = GenerationJobService(db)
    result = await job_svc.get_status(job_id=job_id, project_id=project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or does not belong to this project.",
        )
    return result
