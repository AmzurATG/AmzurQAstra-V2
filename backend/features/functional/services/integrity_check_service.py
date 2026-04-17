"""
Integrity Check Service
Orchestrates browser-use agent runs, persists results to DB, serves poll status.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from features.functional.db.models.integrity_check_result import IntegrityCheckResult
from features.functional.schemas.integrity_check import (
    IntegrityCheckRequest,
    RunStartResponse,
    RunStatusResponse,
)
from features.functional.core.browser.agent_service import (
    BrowserAgentService,
    get_progress,
)
from common.utils.logger import logger


class IntegrityCheckService:
    """Manages the full lifecycle of an integrity check run."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._agent = BrowserAgentService()

    # ── Start ─────────────────────────────────────────────────────────────────

    async def start_check(
        self, request: IntegrityCheckRequest, project_id: int
    ) -> RunStartResponse:
        """
        Persist a pending record, fire the agent as a background task,
        and return the run_id immediately so the client can start polling.
        """
        run_id = str(uuid.uuid4())

        record = IntegrityCheckResult(
            project_id=project_id,
            run_id=run_id,
            status="pending",
            app_url=request.app_url,
            started_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.commit()

        username = request.credentials.username if request.credentials else None
        password = request.credentials.password if request.credentials else None
        # Google Sign-In for BIC is disabled until a supported flow ships (UI forces false too).
        use_google = False

        asyncio.create_task(
            self._run_and_persist(
                run_id, project_id, request.app_url, username, password, use_google
            )
        )

        return RunStartResponse(run_id=run_id, status="pending")

    # ── Background worker ─────────────────────────────────────────────────────

    async def _run_and_persist(
        self,
        run_id: str,
        project_id: int,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
    ) -> None:
        """Run agent then write final result to DB using a fresh session."""
        from common.db.database import async_session_maker

        try:
            result = await self._agent.run(
                run_id, app_url, username, password, use_google_signin
            )
        except Exception as exc:
            logger.error(f"[IntegrityCheck] agent failed run_id={run_id}: {exc}")
            result = {
                "status": "error",
                "overall_status": "error",
                "error": str(exc),
                "screenshots": [],
                "steps": [],
                "steps_total": 0,
                "steps_passed": 0,
                "steps_failed": 0,
                "duration_ms": 0,
                "summary": "",
            }

        async with async_session_maker() as db:
            row_result = await db.execute(
                select(IntegrityCheckResult).where(IntegrityCheckResult.run_id == run_id)
            )
            record = row_result.scalar_one_or_none()
            if record:
                record.status = "error" if result.get("overall_status") == "error" else "completed"
                record.overall_status = result.get("overall_status")
                record.screenshots = result.get("screenshots", [])
                record.steps_data = result.get("steps", [])
                record.steps_total = result.get("steps_total", 0)
                record.steps_passed = result.get("steps_passed", 0)
                record.steps_failed = result.get("steps_failed", 0)
                record.summary = result.get("summary", "")
                record.error_message = result.get("error")
                record.duration_ms = result.get("duration_ms")
                record.completed_at = datetime.utcnow()
                await db.commit()

    # ── Poll status ───────────────────────────────────────────────────────────

    async def get_run_status(self, run_id: str) -> RunStatusResponse:
        """
        Check in-memory store first (live run), fall back to DB (historical).
        """
        progress = get_progress(run_id)
        if progress:
            return RunStatusResponse(
                run_id=run_id,
                status=progress.get("status", "running"),
                percentage=progress.get("percentage", 0),
                current_step=progress.get("current_step"),
                overall_status=progress.get("overall_status"),
                screenshots=progress.get("screenshots", []),
                steps=progress.get("steps", []),
                steps_total=progress.get("steps_total", 0),
                steps_passed=progress.get("steps_passed", 0),
                steps_failed=progress.get("steps_failed", 0),
                summary=progress.get("summary"),
                error=progress.get("error"),
                duration_ms=progress.get("duration_ms"),
            )

        # Fallback: load from DB (e.g. after server restart)
        row_result = await self.db.execute(
            select(IntegrityCheckResult).where(IntegrityCheckResult.run_id == run_id)
        )
        record = row_result.scalar_one_or_none()
        if not record:
            return RunStatusResponse(run_id=run_id, status="not_found", percentage=0)

        pct = 100 if record.status in ("completed", "error") else 0
        return RunStatusResponse(
            run_id=run_id,
            status=record.status,
            percentage=pct,
            overall_status=record.overall_status,
            screenshots=record.screenshots or [],
            steps=record.steps_data or [],
            steps_total=record.steps_total or 0,
            steps_passed=record.steps_passed or 0,
            steps_failed=record.steps_failed or 0,
            summary=record.summary,
            error=record.error_message,
            duration_ms=record.duration_ms,
        )

    # ── History ───────────────────────────────────────────────────────────────

    async def get_history(self, project_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(IntegrityCheckResult)
            .where(IntegrityCheckResult.project_id == project_id)
            .order_by(IntegrityCheckResult.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "status": r.status,
                "app_url": r.app_url,
                "overall_status": r.overall_status,
                "steps_total": r.steps_total,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.scalars().all()
        ]
