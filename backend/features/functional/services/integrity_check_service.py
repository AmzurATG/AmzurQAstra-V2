"""
Integrity Check Service
Orchestrates browser-use agent runs, persists results to DB, serves poll status.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.project import Project
from common.utils.logger import logger
from features.functional.core.browser.agent_service import (
    BrowserAgentService,
    get_progress,
    set_progress,
)
from features.functional.db.models.integrity_check_result import IntegrityCheckResult
from features.functional.schemas.integrity_check import (
    IntegrityCheckRequest,
    RunStartResponse,
    RunStatusResponse,
)
from features.functional.utils.credentials_redaction import redact_known_credentials


def _redact_ic_text(
    text: Optional[str],
    username: Optional[str],
    password: Optional[str],
) -> str:
    if not text:
        return ""
    out = redact_known_credentials(text, username=username, password=password)
    return out if out is not None else ""


async def _verify_app_url_reachable(url: str) -> tuple[bool, Optional[str]]:
    """
    Lightweight HTTP reachability before starting the browser agent.
    Catches common 'app is down' cases (connection refused, timeouts) that the LLM might mis-label as PASS.
    """
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=12.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(
                url,
                headers={"User-Agent": "QAstra-IntegrityCheck/1.0"},
            )
        if r.status_code >= 500:
            return False, f"Server returned HTTP {r.status_code} — the application may be down or misconfigured."
        return True, None
    except httpx.ConnectError as e:
        return (
            False,
            f"Could not connect to the application ({e!s}). Check that the URL is correct and the server is running.",
        )
    except httpx.UnsupportedProtocol:
        return False, "Invalid URL (unsupported protocol)."
    except httpx.TimeoutException:
        return False, "Request timed out — the application did not respond in time."
    except httpx.HTTPError as e:
        return False, f"Could not reach the application: {e!s}"


class IntegrityCheckService:
    """Manages the full lifecycle of an integrity check run."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._agent = BrowserAgentService()

    async def start_check(
        self, request: IntegrityCheckRequest, project_id: int
    ) -> RunStartResponse:
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
        use_google = False

        asyncio.create_task(
            self._run_and_persist(
                run_id, project_id, request.app_url, username, password, use_google
            )
        )

        return RunStartResponse(run_id=run_id, status="pending")

    async def _persist_live_progress(
        self,
        run_id: str,
        payload: Dict[str, Any],
        username: Optional[str],
        password: Optional[str],
    ) -> None:
        from common.db.database import async_session_maker

        raw_summary = payload.get("summary")
        raw_error = payload.get("error")
        safe: Dict[str, Any] = {
            "status": payload.get("status"),
            "percentage": int(payload.get("percentage") or 0),
            "current_step": payload.get("current_step"),
            "overall_status": payload.get("overall_status"),
            "screenshots": list(payload.get("screenshots") or []),
            "steps": list(payload.get("steps") or []),
            "steps_total": int(payload.get("steps_total") or 0),
            "steps_passed": int(payload.get("steps_passed") or 0),
            "steps_failed": int(payload.get("steps_failed") or 0),
            "summary": (_redact_ic_text(raw_summary, username, password) if raw_summary else None),
            "error": (_redact_ic_text(raw_error, username, password) if raw_error else None),
            "duration_ms": payload.get("duration_ms"),
        }
        try:
            async with async_session_maker() as db:
                row_result = await db.execute(
                    select(IntegrityCheckResult).where(IntegrityCheckResult.run_id == run_id)
                )
                record = row_result.scalar_one_or_none()
                if not record:
                    return
                if safe.get("status") == "running":
                    record.status = "running"
                record.live_progress = safe
                await db.commit()
        except Exception as exc:
            logger.warning(f"[IntegrityCheck] live_progress flush failed run_id={run_id}: {exc}")

    async def _run_and_persist(
        self,
        run_id: str,
        project_id: int,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool = False,
    ) -> None:
        from common.db.database import async_session_maker

        async def flush_live(_rid: str, payload: Dict[str, Any]) -> None:
            await self._persist_live_progress(_rid, payload, username, password)

        reachable, reach_err = await _verify_app_url_reachable(app_url)
        if not reachable:
            result: Dict[str, Any] = {
                "status": "completed",
                "overall_status": "failed",
                "percentage": 100,
                "current_step": "Application not reachable",
                "screenshots": [],
                "steps": [],
                "steps_total": 0,
                "steps_passed": 0,
                "steps_failed": 0,
                "summary": reach_err or "Application URL is not reachable.",
                "duration_ms": 0,
                "error": None,
            }
            set_progress(run_id, result)
            async with async_session_maker() as db:
                row_result = await db.execute(
                    select(IntegrityCheckResult).where(IntegrityCheckResult.run_id == run_id)
                )
                record = row_result.scalar_one_or_none()
                if record:
                    record.status = "completed"
                    record.overall_status = "failed"
                    record.app_reachable = False
                    record.live_progress = None
                    record.summary = _redact_ic_text(result["summary"] or "", username, password)
                    record.error_message = None
                    record.screenshots = []
                    record.steps_data = []
                    record.steps_total = 0
                    record.steps_passed = 0
                    record.steps_failed = 0
                    record.duration_ms = 0
                    record.completed_at = datetime.utcnow()
                    await db.commit()
            return

        try:
            result = await self._agent.run(
                run_id,
                app_url,
                username,
                password,
                use_google_signin,
                live_progress_writer=flush_live,
            )
        except Exception as exc:
            logger.error(f"[IntegrityCheck] agent failed run_id={run_id}: {exc}")
            result = {
                "status": "error",
                "overall_status": "error",
                "error": _redact_ic_text(str(exc), username, password),
                "screenshots": [],
                "steps": [],
                "steps_total": 0,
                "steps_passed": 0,
                "steps_failed": 0,
                "duration_ms": 0,
                "summary": "",
            }
            set_progress(run_id, result)

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
                record.summary = _redact_ic_text(result.get("summary") or "", username, password)
                record.error_message = (
                    _redact_ic_text(result.get("error"), username, password) or None
                )
                record.duration_ms = result.get("duration_ms")
                record.completed_at = datetime.utcnow()
                record.live_progress = None
                if result.get("overall_status") in ("passed", "failed"):
                    record.app_reachable = True
                await db.commit()

    async def _project_credential_strings_for_ic_run(
        self, run_id: str
    ) -> tuple[Optional[str], Optional[str]]:
        row_result = await self.db.execute(
            select(IntegrityCheckResult).where(IntegrityCheckResult.run_id == run_id)
        )
        rec = row_result.scalar_one_or_none()
        if not rec:
            return None, None
        prow = await self.db.execute(select(Project).where(Project.id == rec.project_id))
        proj = prow.scalar_one_or_none()
        if not proj or not proj.app_credentials:
            return None, None
        c = proj.app_credentials or {}
        return c.get("username"), c.get("password")

    def _run_status_from_live_dict(
        self,
        run_id: str,
        progress: Dict[str, Any],
        bu: Optional[str],
        bp: Optional[str],
    ) -> RunStatusResponse:
        s_raw = progress.get("summary")
        e_raw = progress.get("error")
        summ_p = _redact_ic_text(s_raw, bu, bp) if s_raw else ""
        err_p = _redact_ic_text(e_raw, bu, bp) if e_raw else ""
        return RunStatusResponse(
            run_id=run_id,
            status=progress.get("status", "running"),
            percentage=int(progress.get("percentage") or 0),
            current_step=progress.get("current_step"),
            overall_status=progress.get("overall_status"),
            screenshots=list(progress.get("screenshots") or []),
            steps=list(progress.get("steps") or []),
            steps_total=int(progress.get("steps_total") or 0),
            steps_passed=int(progress.get("steps_passed") or 0),
            steps_failed=int(progress.get("steps_failed") or 0),
            summary=summ_p or None,
            error=err_p or None,
            duration_ms=progress.get("duration_ms"),
        )

    async def get_run_status(self, run_id: str) -> RunStatusResponse:
        bu, bp = await self._project_credential_strings_for_ic_run(run_id)

        progress = get_progress(run_id)
        if progress:
            return self._run_status_from_live_dict(run_id, progress, bu, bp)

        row_result = await self.db.execute(
            select(IntegrityCheckResult).where(IntegrityCheckResult.run_id == run_id)
        )
        record = row_result.scalar_one_or_none()
        if not record:
            return RunStatusResponse(run_id=run_id, status="not_found", percentage=0)

        if record.live_progress and isinstance(record.live_progress, dict):
            lp = record.live_progress
            lp_status = lp.get("status") or record.status
            if lp_status in ("running", "completed", "error") or record.status in (
                "pending",
                "running",
            ):
                return self._run_status_from_live_dict(run_id, lp, bu, bp)

        pct = 100 if record.status in ("completed", "error") else 0
        summ = _redact_ic_text(record.summary, bu, bp) if record.summary else ""
        err = _redact_ic_text(record.error_message, bu, bp) if record.error_message else ""
        summ = summ or None
        err = err or None
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
            summary=summ,
            error=err,
            duration_ms=record.duration_ms,
        )

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