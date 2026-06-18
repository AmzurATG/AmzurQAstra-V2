"""
Test Run Report Service

Manages background PDF generation for functional test runs.

Job lifecycle:
  "not_started"  → no record in _jobs (or DB report_path is None)
  "generating"   → asyncio task running, _jobs[run_id].status == "generating"
  "ready"        → pdf written, _jobs[run_id].status == "ready" AND test_runs.report_path set
  "failed"       → generation error, _jobs[run_id].status == "failed"
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.db.models.project import Project
from common.db.models.user_story import UserStory
from common.utils.logger import logger
from config import settings
from features.functional.db.models.requirement import Requirement
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun
from features.functional.services.test_run_report_pdf import build_test_run_report_pdf


# ---------------------------------------------------------------------------
# In-memory job status registry
# ---------------------------------------------------------------------------

class _ReportJobManager:
    """Singleton in-memory store for report generation job status."""

    _instance: Optional["_ReportJobManager"] = None
    _jobs: Dict[int, Dict[str, Any]]

    def __new__(cls) -> "_ReportJobManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._jobs = {}
        return cls._instance

    def start(self, run_id: int) -> None:
        self._jobs[run_id] = {
            "status": "generating",
            "pdf_path": None,
            "error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    def set_ready(self, run_id: int, pdf_path: str) -> None:
        self._jobs[run_id] = {
            "status": "ready",
            "pdf_path": pdf_path,
            "error": None,
            "started_at": self._jobs.get(run_id, {}).get("started_at"),
        }

    def set_failed(self, run_id: int, error: str) -> None:
        self._jobs[run_id] = {
            "status": "failed",
            "pdf_path": None,
            "error": error,
            "started_at": self._jobs.get(run_id, {}).get("started_at"),
        }

    def get(self, run_id: int) -> Optional[Dict[str, Any]]:
        return self._jobs.get(run_id)

    def is_generating(self, run_id: int) -> bool:
        job = self._jobs.get(run_id)
        return job is not None and job["status"] == "generating"

    def clear(self, run_id: int) -> None:
        self._jobs.pop(run_id, None)


_job_manager = _ReportJobManager()


# ---------------------------------------------------------------------------
# PDF storage helpers
# ---------------------------------------------------------------------------

def _pdf_storage_path(project_id: int, run_id: int) -> Path:
    base = Path(settings.STORAGE_LOCAL_PATH).resolve()
    subdir = base / "TestRunReports" / str(project_id)
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / f"run_{run_id}.pdf"


# ---------------------------------------------------------------------------
# Data fetcher
# ---------------------------------------------------------------------------

async def _fetch_report_data(db: AsyncSession, run_id: int) -> Dict[str, Any]:
    """
    Load all data needed to build the report in a single DB round-trip sequence.
    Returns a dict with keys:
        run, project, results, requirements, user_stories
    """
    # 1. TestRun with results → test_case → steps
    run_q = await db.execute(
        select(TestRun)
        .options(
            selectinload(TestRun.test_results)
            .selectinload(TestResult.test_case)
            .selectinload(TestCase.steps)
        )
        .where(TestRun.id == run_id)
    )
    run: Optional[TestRun] = run_q.scalar_one_or_none()
    if not run:
        raise ValueError(f"Test run {run_id} not found")

    # 2. Project
    proj_q = await db.execute(select(Project).where(Project.id == run.project_id))
    project: Optional[Project] = proj_q.scalar_one_or_none()

    results = run.test_results or []

    # 3. Unique user story IDs
    story_ids = {
        r.test_case.user_story_id
        for r in results
        if r.test_case and r.test_case.user_story_id
    }
    user_stories: Dict[int, Dict[str, Any]] = {}
    if story_ids:
        stories_q = await db.execute(select(UserStory).where(UserStory.id.in_(story_ids)))
        for us in stories_q.scalars().all():
            user_stories[us.id] = {
                "id": us.id,
                "external_key": us.external_key or us.external_id,
                "title": us.title,
                "description": us.description,
                "acceptance_criteria": us.acceptance_criteria,
                "status": us.status.value if us.status else None,
                "priority": us.priority.value if us.priority else None,
            }

    # 4. Unique requirement IDs
    req_ids = {
        r.test_case.requirement_id
        for r in results
        if r.test_case and r.test_case.requirement_id
    }
    requirements: Dict[int, Dict[str, Any]] = {}
    if req_ids:
        reqs_q = await db.execute(select(Requirement).where(Requirement.id.in_(req_ids)))
        for req in reqs_q.scalars().all():
            requirements[req.id] = {
                "id": req.id,
                "title": req.title,
                "file_name": req.file_name,
            }

    # 5. Serialise results into plain dicts (avoid lazy-load issues outside session)
    result_dicts = []
    for r in sorted(results, key=lambda x: x.test_case.case_number if x.test_case else 0):
        tc = r.test_case
        result_dicts.append({
            "id": r.id,
            "status": r.status.value if r.status else "unknown",
            "duration_ms": r.duration_ms,
            "error_message": r.error_message,
            "error_stack": r.error_stack,
            "failed_step": r.failed_step,
            "screenshot_path": r.screenshot_path,
            "step_results": r.step_results or [],
            "adapted_steps": r.adapted_steps or [],
            "original_steps": r.original_steps or [],
            "agent_logs": r.agent_logs or [],
            "test_case": {
                "id": tc.id,
                "case_number": tc.case_number,
                "title": tc.title,
                "description": tc.description,
                "preconditions": tc.preconditions,
                "priority": tc.priority.value if tc.priority else None,
                "category": tc.category.value if tc.category else None,
                "scenario_type": tc.scenario_type,
                "tags": tc.tags,
                "user_story_id": tc.user_story_id,
                "requirement_id": tc.requirement_id,
                "steps": [
                    {
                        "step_number": s.step_number,
                        "action": s.action,
                        "target": s.target,
                        "description": s.description,
                        "expected_result": s.expected_result,
                    }
                    for s in (tc.steps or [])
                ],
            } if tc else {},
        })

    return {
        "run": run,
        "project": project,
        "results": result_dicts,
        "requirements": requirements,
        "user_stories": user_stories,
    }


# ---------------------------------------------------------------------------
# Background generation task
# ---------------------------------------------------------------------------

async def _generate_report_task(run_id: int, project_id: int) -> None:
    """
    Coroutine run as a background asyncio task.
    Creates its own DB session (safe to run outside the request lifecycle).
    """
    from common.db.database import async_session_maker  # lazy import avoids circular deps

    logger.info("Report generation started for run_id=%s", run_id)
    try:
        async with async_session_maker() as db:
            data = await _fetch_report_data(db, run_id)

            run: TestRun = data["run"]
            project: Optional[Project] = data["project"]

            pdf_bytes = build_test_run_report_pdf(
                project_name=project.name if project else f"Project #{run.project_id}",
                run_number=run.run_number or run.id,
                run_name=run.name,
                run_status=run.status.value if run.status else "unknown",
                run_browser=run.browser,
                run_started_at=run.started_at,
                run_completed_at=run.completed_at,
                total_tests=run.total_tests or 0,
                passed_tests=run.passed_tests or 0,
                failed_tests=run.failed_tests or 0,
                skipped_tests=run.skipped_tests or 0,
                results=data["results"],
                requirements=data["requirements"],
                user_stories=data["user_stories"],
                screenshots_dir=settings.SCREENSHOTS_DIR,
            )

            pdf_path = _pdf_storage_path(run.project_id, run_id)
            pdf_path.write_bytes(pdf_bytes)

            # Write path back to test_runs.report_path
            await db.execute(
                update(TestRun)
                .where(TestRun.id == run_id)
                .values(report_path=str(pdf_path))
            )
            await db.commit()

        _job_manager.set_ready(run_id, str(pdf_path))
        logger.info("Report generation complete for run_id=%s (%.1f KB)", run_id, len(pdf_bytes) / 1024)

    except Exception as exc:
        logger.exception("Report generation failed for run_id=%s: %s", run_id, exc)
        _job_manager.set_failed(run_id, str(exc))


def _sync_generate_wrapper(run_id: int, project_id: int) -> None:
    """Synchronous wrapper for Windows ProactorEventLoop (same pattern as test execution)."""
    policy = asyncio.WindowsProactorEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_generate_report_task(run_id, project_id))
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------

class TestRunReportService:
    """FastAPI-level service: coordinate background report generation and delivery."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_status(self, run_id: int) -> Dict[str, Any]:
        """
        Return current report status for a run.
        Checks in-memory job first, then DB (for reports generated in a previous session).
        """
        job = _job_manager.get(run_id)
        if job:
            return {
                "run_id": run_id,
                "status": job["status"],
                "pdf_path": job["pdf_path"],
                "error": job["error"],
            }

        # Fall back to DB
        row = (await self.db.execute(
            select(TestRun.report_path, TestRun.status).where(TestRun.id == run_id)
        )).one_or_none()

        if row is None:
            return {"run_id": run_id, "status": "not_found", "pdf_path": None, "error": None}

        report_path, run_status = row
        if report_path and Path(report_path).exists():
            return {"run_id": run_id, "status": "ready", "pdf_path": report_path, "error": None}

        return {"run_id": run_id, "status": "not_started", "pdf_path": None, "error": None}

    async def generate(self, run_id: int, *, force: bool = False) -> Dict[str, Any]:
        """
        Kick off background report generation (idempotent unless ``force`` is True).
        Returns immediately with the current job status.
        """
        # Already generating?
        if _job_manager.is_generating(run_id):
            return {"run_id": run_id, "status": "generating", "message": "Report generation is already in progress."}

        # Already in DB?
        row = (await self.db.execute(
            select(TestRun.report_path, TestRun.project_id, TestRun.status)
            .where(TestRun.id == run_id)
        )).one_or_none()

        if row is None:
            return {"run_id": run_id, "status": "not_found", "message": "Test run not found."}

        report_path, project_id, run_status = row

        if report_path and Path(report_path).exists() and not force:
            # Re-cache in memory and return immediately
            _job_manager.set_ready(run_id, report_path)
            return {"run_id": run_id, "status": "ready", "message": "Report already generated — ready to download."}

        if force:
            _job_manager.clear(run_id)

        # Start background task
        _job_manager.start(run_id)

        if sys.platform == "win32":
            asyncio.create_task(
                asyncio.to_thread(_sync_generate_wrapper, run_id, project_id)
            )
        else:
            asyncio.create_task(_generate_report_task(run_id, project_id))

        return {"run_id": run_id, "status": "generating", "message": "Report generation started. Poll /status for updates."}

    async def get_pdf_bytes(self, run_id: int) -> Optional[bytes]:
        """Return PDF bytes if the report is ready, else None."""
        status_info = await self.get_status(run_id)
        pdf_path = status_info.get("pdf_path")
        if not pdf_path:
            return None
        p = Path(pdf_path)
        if not p.exists():
            return None
        return p.read_bytes()

    async def get_pdf_path(self, run_id: int) -> Optional[str]:
        """Return the file path to the generated PDF if ready."""
        status_info = await self.get_status(run_id)
        pdf_path = status_info.get("pdf_path")
        if pdf_path and Path(pdf_path).exists():
            return pdf_path
        return None

    async def send_email(self, run_id: int, to_addr: str) -> None:
        """Email the generated PDF report to ``to_addr``."""
        from common.services.smtp_mailer import (
            send_email_with_pdf_attachment,
            SmtpSendError,
            is_smtp_configured,
        )

        if not is_smtp_configured():
            raise SmtpSendError("Email is not configured (set SMTP_HOST and EMAIL_FROM_ADDRESS).")

        pdf_bytes = await self.get_pdf_bytes(run_id)
        if not pdf_bytes:
            raise ValueError("Report is not ready yet. Generate and wait for completion before emailing.")

        # Fetch run meta for subject line
        row = (await self.db.execute(
            select(TestRun.run_number, TestRun.name, TestRun.status, TestRun.completed_at,
                   TestRun.total_tests, TestRun.passed_tests, TestRun.failed_tests, TestRun.project_id)
            .where(TestRun.id == run_id)
        )).one_or_none()

        if row is None:
            raise ValueError("Test run not found.")

        run_number, run_name, run_status, completed_at, total, passed, failed, project_id = row

        proj_row = (await self.db.execute(select(Project.name).where(Project.id == project_id))).scalar_one_or_none()
        project_name = proj_row or f"Project #{project_id}"

        pass_rate = round(passed / total * 100) if total else 0
        subject = (
            f"{settings.APP_NAME} — Test Run #{run_number} Report "
            f"({run_status.value if hasattr(run_status, 'value') else run_status} | {pass_rate}% pass rate)"
        )

        _dt = completed_at
        if _dt and _dt.tzinfo is None:
            _dt = _dt.replace(tzinfo=timezone.utc)
        dt_str = _dt.strftime("%Y-%m-%d %H:%M UTC") if _dt else "—"

        text_body = (
            f"Hello,\n\n"
            f"Please find attached the Test Execution Report for {project_name}.\n\n"
            f"  Run #:       {run_number}\n"
            f"  Run name:    {run_name or '—'}\n"
            f"  Status:      {run_status.value if hasattr(run_status, 'value') else run_status}\n"
            f"  Completed:   {dt_str}\n"
            f"  Total tests: {total} ({passed} passed, {failed} failed)\n"
            f"  Pass rate:   {pass_rate}%\n\n"
            f"The full report is attached as a PDF.\n\n"
            f"Kind regards,\n{settings.APP_NAME}\n"
        )

        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;color:#1a1a1a;">
<p>Hello,</p>
<p>Please find attached the <strong>Test Execution Report</strong> for <strong>{project_name}</strong>.</p>
<ul style="margin:0 0 1em 1.2em;padding:0;line-height:1.8;">
  <li>Run #: <strong>{run_number}</strong></li>
  <li>Run name: <strong>{run_name or '—'}</strong></li>
  <li>Status: <strong>{run_status.value if hasattr(run_status, 'value') else run_status}</strong></li>
  <li>Completed: <strong>{dt_str}</strong></li>
  <li>Total tests: <strong>{total}</strong> ({passed} passed, {failed} failed)</li>
  <li>Pass rate: <strong>{pass_rate}%</strong></li>
</ul>
<p>The full report is attached as a PDF. Screenshots and step-by-step details are included in the document.</p>
<p style="margin-top:1.5em;">Kind regards,<br><strong>{settings.APP_NAME}</strong></p>
</body></html>"""

        filename = f"QAstra_TestRun_{run_number}_Report.pdf"

        # Size-adaptive: if PDF > 8 MB warn (still send — SMTP limit handling varies)
        size_mb = len(pdf_bytes) / (1024 * 1024)
        if size_mb > 8:
            logger.warning(
                "Test run report PDF is %.1f MB — may exceed some SMTP attachment limits.", size_mb
            )

        send_email_with_pdf_attachment(
            to_addr=to_addr,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            pdf_bytes=pdf_bytes,
            attachment_filename=filename,
        )
