"""
Integrity Check Repository

All database read/write operations for integrity check runs and step results.
Extracted from IntegrityCheckService to keep each class focused and under
the 400-line limit.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common.db.models.integrity_check_run import IntegrityCheckRun, IntegrityCheckStepResult
from common.utils.logger import logger


class IntegrityCheckRepository:
    """Persistence layer for integrity check runs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run(
        self,
        project_id: int,
        app_url: str,
        browser_engine: str,
        auth_method: str,
        triggered_by: Optional[int] = None,
    ) -> IntegrityCheckRun:
        """Create a new run record with status=running."""
        run = IntegrityCheckRun(
            project_id=project_id,
            triggered_by=triggered_by,
            status="running",
            app_url=app_url,
            browser_engine=browser_engine,
            auth_method=auth_method,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        logger.info(f"[ICRepo] Created run id={run.id}")
        return run

    async def finalise_run(
        self,
        run: IntegrityCheckRun,
        status: str,
        app_reachable: bool,
        login_successful: Optional[bool],
        test_cases_total: int,
        test_cases_passed: int,
        test_cases_failed: int,
        duration_ms: int,
        error: Optional[str] = None,
    ) -> IntegrityCheckRun:
        """Update the run record with final aggregated results."""
        run.status = status
        run.app_reachable = app_reachable
        run.login_successful = login_successful
        run.test_cases_total = test_cases_total
        run.test_cases_passed = test_cases_passed
        run.test_cases_failed = test_cases_failed
        run.duration_ms = duration_ms
        run.error = error
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def save_step_result(
        self,
        run_id: int,
        test_case_id: Optional[int],
        test_case_title: str,
        test_case_status: Optional[str],
        test_case_duration_ms: Optional[int],
        step_number: int,
        action: str,
        description: Optional[str],
        status: str,
        error: Optional[str],
        screenshot_path: Optional[str],
        llm_diagnosis: Optional[str],
        duration_ms: int,
    ) -> IntegrityCheckStepResult:
        """Persist one step result row."""
        row = IntegrityCheckStepResult(
            run_id=run_id,
            test_case_id=test_case_id,
            test_case_title=test_case_title,
            test_case_status=test_case_status,
            test_case_duration_ms=test_case_duration_ms,
            step_number=step_number,
            action=action,
            description=description,
            status=status,
            error=error,
            screenshot_path=screenshot_path,
            llm_diagnosis=llm_diagnosis,
            duration_ms=duration_ms,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_run_history(
        self, project_id: int, limit: int = 20
    ) -> List[IntegrityCheckRun]:
        """Return recent runs for a project, newest first, with step results eager-loaded."""
        result = await self.db.execute(
            select(IntegrityCheckRun)
            .options(selectinload(IntegrityCheckRun.step_results))
            .where(IntegrityCheckRun.project_id == project_id)
            .order_by(IntegrityCheckRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_run_by_id(self, run_id: int) -> Optional[IntegrityCheckRun]:
        """Return a single run with all step results."""
        result = await self.db.execute(
            select(IntegrityCheckRun)
            .options(selectinload(IntegrityCheckRun.step_results))
            .where(IntegrityCheckRun.id == run_id)
        )
        return result.scalar_one_or_none()
