"""
Generation Job Service — CRUD + status management for GenerationJob rows.

Keeps DB operations separate from orchestration logic (bulk_generation_service).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.db.models.generation_job import GenerationJob, GenerationJobStatus
from features.functional.schemas.bulk_generation import GenerationJobStatusResponse

logger = logging.getLogger(__name__)


class GenerationJobService:
    """Manages GenerationJob lifecycle: create → update progress → complete/fail."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_job(
        self,
        project_id: int,
        story_ids: List[int],
        profile: str,
        created_by: Optional[int],
    ) -> GenerationJob:
        job = GenerationJob(
            project_id=project_id,
            created_by=created_by,
            status=GenerationJobStatus.queued,
            profile=profile,
            story_ids=story_ids,
            total_stories=len(story_ids),
            completed_stories=0,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        logger.info(
            "GenerationJob created id=%s project=%s stories=%s profile=%s",
            job.id, project_id, len(story_ids), profile,
        )
        return job

    async def mark_running(self, job_id: int) -> None:
        job = await self._get(job_id)
        if not job:
            return
        job.status = GenerationJobStatus.running
        await self.db.commit()

    async def update_progress(
        self,
        job_id: int,
        completed_stories: int,
        current_story_title: Optional[str],
    ) -> None:
        job = await self._get(job_id)
        if not job:
            return
        job.completed_stories = completed_stories
        job.current_story_title = current_story_title
        await self.db.commit()

    async def mark_completed(
        self, job_id: int, coverage_report: List[Dict[str, Any]]
    ) -> None:
        job = await self._get(job_id)
        if not job:
            return
        job.status = GenerationJobStatus.completed
        job.completed_stories = job.total_stories
        job.current_story_title = None
        job.coverage_report_json = coverage_report
        await self.db.commit()
        logger.info("GenerationJob completed id=%s", job_id)

    async def mark_failed(self, job_id: int, error: str) -> None:
        job = await self._get(job_id)
        if not job:
            return
        job.status = GenerationJobStatus.failed
        job.error_message = str(error)[:2000]
        await self.db.commit()
        logger.error("GenerationJob failed id=%s: %s", job_id, error)

    async def get_status(
        self, job_id: int, project_id: int
    ) -> Optional[GenerationJobStatusResponse]:
        job = await self._get_scoped(job_id, project_id)
        if not job:
            return None
        return self._to_response(job)

    async def _get(self, job_id: int) -> Optional[GenerationJob]:
        return await self.db.get(GenerationJob, job_id)

    async def _get_scoped(
        self, job_id: int, project_id: int
    ) -> Optional[GenerationJob]:
        res = await self.db.execute(
            select(GenerationJob).where(
                GenerationJob.id == job_id,
                GenerationJob.project_id == project_id,
            )
        )
        return res.scalar_one_or_none()

    @staticmethod
    def _to_response(job: GenerationJob) -> GenerationJobStatusResponse:
        pct = (
            round(job.completed_stories / job.total_stories * 100, 1)
            if job.total_stories > 0
            else 0.0
        )
        return GenerationJobStatusResponse(
            job_id=job.id,
            project_id=job.project_id,
            status=job.status,
            profile=job.profile,
            total_stories=job.total_stories,
            completed_stories=job.completed_stories,
            current_story_title=job.current_story_title,
            progress_percent=pct,
            coverage_report=job.coverage_report_json,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
