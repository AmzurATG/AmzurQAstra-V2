"""
Test Execution Service - Run tests via MCP server
"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from common.api.pagination import PaginationParams
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.schemas.test_run import TestRunCreate
from features.functional.core.mcp_client.client import MCPClient


class TestExecutionService:
    """Service for test execution operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mcp_client = MCPClient()
    
    async def get_runs(
        self,
        project_id: int,
        status: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[TestRun], int]:
        """Get test runs for a project."""
        query = select(TestRun).where(TestRun.project_id == project_id)
        count_query = select(func.count(TestRun.id)).where(
            TestRun.project_id == project_id
        )
        
        if status:
            query = query.where(TestRun.status == status)
            count_query = count_query.where(TestRun.status == status)
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        
        query = query.order_by(TestRun.created_at.desc())
        
        result = await self.db.execute(query)
        runs = result.scalars().all()
        
        return list(runs), total
    
    async def get_run_with_results(self, run_id: int) -> Optional[TestRun]:
        """Get test run with all results."""
        result = await self.db.execute(
            select(TestRun)
            .options(selectinload(TestRun.test_results))
            .where(TestRun.id == run_id)
        )
        return result.scalar_one_or_none()
    
    async def create_run(
        self, run_data: TestRunCreate, triggered_by: int
    ) -> TestRun:
        """Create a new test run."""
        # Get test cases
        if run_data.test_case_ids:
            result = await self.db.execute(
                select(TestCase)
                .where(TestCase.id.in_(run_data.test_case_ids))
                .where(TestCase.project_id == run_data.project_id)
            )
            test_cases = result.scalars().all()
        else:
            result = await self.db.execute(
                select(TestCase)
                .where(TestCase.project_id == run_data.project_id)
            )
            test_cases = result.scalars().all()
        
        # Create test run
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
        
        # Create test results (pending)
        for test_case in test_cases:
            result = TestResult(
                test_run_id=test_run.id,
                test_case_id=test_case.id,
                status=TestResultStatus.SKIPPED,
            )
            self.db.add(result)
        
        await self.db.flush()
        await self.db.refresh(test_run)
        
        return test_run
    
    async def execute_run(self, run_id: int) -> Optional[TestRun]:
        """Execute a pending test run."""
        test_run = await self.get_run_with_results(run_id)
        if not test_run:
            return None
        
        if test_run.status != TestRunStatus.PENDING:
            return test_run
        
        # Update status
        test_run.status = TestRunStatus.RUNNING
        test_run.started_at = datetime.utcnow()
        await self.db.flush()
        
        # Execute tests
        passed = 0
        failed = 0
        
        for test_result in test_run.test_results:
            try:
                # Get test case with steps
                tc_result = await self.db.execute(
                    select(TestCase)
                    .options(selectinload(TestCase.steps))
                    .where(TestCase.id == test_result.test_case_id)
                )
                test_case = tc_result.scalar_one()
                
                # Execute via MCP
                start_time = datetime.utcnow()
                execution_result = await self.mcp_client.execute_test_case(test_case)
                end_time = datetime.utcnow()
                
                # Update result
                test_result.status = (
                    TestResultStatus.PASSED if execution_result["success"]
                    else TestResultStatus.FAILED
                )
                test_result.duration_ms = int(
                    (end_time - start_time).total_seconds() * 1000
                )
                test_result.started_at = start_time
                test_result.completed_at = end_time
                test_result.step_results = execution_result.get("step_results")
                test_result.screenshot_path = execution_result.get("screenshot_path")
                
                if not execution_result["success"]:
                    test_result.error_message = execution_result.get("error")
                    test_result.failed_step = execution_result.get("failed_step")
                    failed += 1
                else:
                    passed += 1
                
            except Exception as e:
                test_result.status = TestResultStatus.ERROR
                test_result.error_message = str(e)
                failed += 1
        
        # Update run summary
        test_run.status = TestRunStatus.PASSED if failed == 0 else TestRunStatus.FAILED
        test_run.completed_at = datetime.utcnow()
        test_run.passed_tests = passed
        test_run.failed_tests = failed
        
        await self.db.flush()
        await self.db.refresh(test_run)
        
        return test_run
    
    async def cancel_run(self, run_id: int) -> Optional[TestRun]:
        """Cancel a running test run."""
        test_run = await self.get_run_with_results(run_id)
        if not test_run:
            return None
        
        if test_run.status not in [TestRunStatus.PENDING, TestRunStatus.RUNNING]:
            return test_run
        
        test_run.status = TestRunStatus.CANCELLED
        test_run.completed_at = datetime.utcnow()
        
        await self.db.flush()
        await self.db.refresh(test_run)
        
        return test_run
    
    async def get_results(self, run_id: int) -> List[TestResult]:
        """Get all results for a test run."""
        result = await self.db.execute(
            select(TestResult).where(TestResult.test_run_id == run_id)
        )
        return list(result.scalars().all())
    
    async def get_screenshot_path(self, result_id: int) -> Optional[str]:
        """Get screenshot path for a test result."""
        result = await self.db.execute(
            select(TestResult).where(TestResult.id == result_id)
        )
        test_result = result.scalar_one_or_none()
        if test_result and test_result.screenshot_path:
            return test_result.screenshot_path
        return None
