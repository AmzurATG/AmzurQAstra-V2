"""
Test Execution Service

Executes test runs by running each test case's steps through the
browser automation layer (PlaywrightRunner by default).
Replaces the previous MCP-server-based execution path.
"""
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from common.api.pagination import PaginationParams
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.schemas.test_run import TestRunCreate
from features.functional.core.browser.factory import get_browser_runner
from common.utils.logger import logger


class TestExecutionService:
    """Service for test run creation and execution."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_runs(
        self,
        project_id: int,
        status: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[TestRun], int]:
        query = select(TestRun).where(TestRun.project_id == project_id)
        count_query = select(func.count(TestRun.id)).where(TestRun.project_id == project_id)

        if status:
            query = query.where(TestRun.status == status)
            count_query = count_query.where(TestRun.status == status)

        total = (await self.db.execute(count_query)).scalar()

        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        query = query.order_by(TestRun.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_run_with_results(self, run_id: int) -> Optional[TestRun]:
        result = await self.db.execute(
            select(TestRun)
            .options(selectinload(TestRun.test_results))
            .where(TestRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_results(self, run_id: int) -> List[TestResult]:
        result = await self.db.execute(
            select(TestResult).where(TestResult.test_run_id == run_id)
        )
        return list(result.scalars().all())

    async def get_screenshot_path(self, result_id: int) -> Optional[str]:
        result = await self.db.execute(
            select(TestResult).where(TestResult.id == result_id)
        )
        tr = result.scalar_one_or_none()
        return tr.screenshot_path if tr else None

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_run(self, run_data: TestRunCreate, triggered_by: int) -> TestRun:
        if run_data.test_case_ids:
            result = await self.db.execute(
                select(TestCase)
                .where(TestCase.id.in_(run_data.test_case_ids))
                .where(TestCase.project_id == run_data.project_id)
            )
        else:
            result = await self.db.execute(
                select(TestCase).where(TestCase.project_id == run_data.project_id)
            )
        test_cases = result.scalars().all()

        test_run = TestRun(
            project_id=run_data.project_id,
            name=run_data.name or f"Test Run {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            description=run_data.description,
            status=TestRunStatus.PENDING,
            triggered_by=triggered_by,
            total_tests=len(test_cases),
            browser=run_data.browser,
            headless=str(run_data.headless).lower(),
            config=run_data.config,
        )
        self.db.add(test_run)
        await self.db.flush()

        for tc in test_cases:
            self.db.add(TestResult(
                test_run_id=test_run.id,
                test_case_id=tc.id,
                status=TestResultStatus.SKIPPED,
            ))

        await self.db.flush()
        await self.db.refresh(test_run)
        return test_run

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute_run(self, run_id: int) -> Optional[TestRun]:
        test_run = await self.get_run_with_results(run_id)
        if not test_run or test_run.status != TestRunStatus.PENDING:
            return test_run

        test_run.status = TestRunStatus.RUNNING
        test_run.started_at = datetime.utcnow()
        await self.db.flush()

        passed = failed = 0

        async with get_browser_runner(headless=True, engine=test_run.browser) as runner:
            for test_result in test_run.test_results:
                try:
                    tc_result = await self.db.execute(
                        select(TestCase)
                        .options(selectinload(TestCase.steps))
                        .where(TestCase.id == test_result.test_case_id)
                    )
                    test_case = tc_result.scalar_one()

                    start_time = datetime.utcnow()
                    success, error_msg, screenshot_path = await self._run_test_case(
                        runner, test_case, test_run.project_id, run_id,
                    )
                    end_time = datetime.utcnow()

                    test_result.status = TestResultStatus.PASSED if success else TestResultStatus.FAILED
                    test_result.duration_ms = int((end_time - start_time).total_seconds() * 1000)
                    test_result.started_at = start_time
                    test_result.completed_at = end_time
                    test_result.screenshot_path = screenshot_path
                    if not success:
                        test_result.error_message = error_msg
                        failed += 1
                    else:
                        passed += 1

                except Exception as e:
                    test_result.status = TestResultStatus.ERROR
                    test_result.error_message = str(e)
                    failed += 1

        test_run.status = TestRunStatus.PASSED if failed == 0 else TestRunStatus.FAILED
        test_run.completed_at = datetime.utcnow()
        test_run.passed_tests = passed
        test_run.failed_tests = failed
        await self.db.flush()
        await self.db.refresh(test_run)
        return test_run

    async def cancel_run(self, run_id: int) -> Optional[TestRun]:
        test_run = await self.get_run_with_results(run_id)
        if not test_run:
            return None
        if test_run.status in [TestRunStatus.PENDING, TestRunStatus.RUNNING]:
            test_run.status = TestRunStatus.CANCELLED
            test_run.completed_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(test_run)
        return test_run

    # ------------------------------------------------------------------
    # Internal step runner
    # ------------------------------------------------------------------

    async def _run_test_case(
        self,
        runner,
        test_case: TestCase,
        project_id: int,
        run_id: int,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Run all steps; return (success, error_message, last_screenshot_path)."""
        from config import settings
        from pathlib import Path

        screenshots_dir = Path(settings.SCREENSHOTS_DIR) / str(project_id) / str(run_id)
        last_screenshot: Optional[str] = None

        for step in sorted(test_case.steps, key=lambda s: s.step_number):
            action = step.action.value if hasattr(step.action, "value") else str(step.action)

            if action == "navigate":
                result = await runner.navigate(step.target or step.value or "")
            elif action == "click":
                result = await runner.click(step.target or "")
            elif action in ("fill", "type"):
                result = await runner.fill(step.target or "", step.value or "")
            elif action == "select":
                result = await runner.select_option(step.target or "", step.value or "")
            elif action == "hover":
                result = await runner.hover(step.target or "")
            elif action == "wait":
                ms = int(step.value) if step.value and step.value.isdigit() else 1000
                result = await runner.wait(ms)
            elif action == "assert_visible":
                result = await runner.assert_visible(step.target or "")
            elif action == "assert_text":
                result = await runner.assert_text(step.target or "", step.value or "")
            elif action == "assert_url":
                result = await runner.assert_url(step.target or step.value or "")
            else:
                continue  # Skip unknown actions gracefully

            # Capture screenshot after every step
            try:
                safe_action = "".join(c if c.isalnum() else "_" for c in action)
                fname = f"step_{step.step_number:03d}_{safe_action}.png"
                fpath = screenshots_dir / fname
                await runner.screenshot(path=str(fpath))
                last_screenshot = f"/screenshots/{project_id}/{run_id}/{fname}"
            except Exception:
                pass

            if not result.success:
                return False, result.error, last_screenshot

        return True, None, last_screenshot
