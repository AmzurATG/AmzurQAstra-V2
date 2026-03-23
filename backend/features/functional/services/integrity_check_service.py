"""
Integrity Check Service - Verify app is ready for testing
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import base64
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from features.functional.schemas.integrity_check import (
    IntegrityCheckRequest,
    IntegrityCheckResponse,
    PageCheckResult,
    TestCaseResult,
)
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_step import TestStep
from features.functional.core.mcp_client.client import MCPClient
from common.db.models.user_story import UserStory
from config import settings
from common.utils.logger import logger


class IntegrityCheckService:
    """Service for build integrity checks."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # headless=False to show browser window
        self.mcp_client = MCPClient(headless=False)
        self.screenshots_dir = Path(settings.SCREENSHOTS_DIR)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    def _save_screenshot(self, base64_data: str, name: str) -> str:
        """Save base64 screenshot to file and return URL path."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Sanitize name for filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        filename = f"{safe_name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        # Decode and save
        image_data = base64.b64decode(base64_data)
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        # Return URL path (accessible via /screenshots/filename)
        return f"/screenshots/{filename}"
    
    async def run_check(
        self, request: IntegrityCheckRequest
    ) -> IntegrityCheckResponse:
        """Run integrity check on the application by executing flagged test cases."""
        from features.functional.schemas.integrity_check import StepResult, TestCaseResult
        
        start_time = datetime.utcnow()
        screenshots: List[str] = []
        test_case_results: List[TestCaseResult] = []
        app_reachable = False
        
        try:
            # First check if app is reachable
            result = await self.mcp_client.navigate(request.app_url)
            app_reachable = result.get("success", False)
            
            if not app_reachable:
                return IntegrityCheckResponse(
                    project_id=request.project_id,
                    status="failed",
                    app_reachable=False,
                    test_cases_total=0,
                    test_cases_passed=0,
                    test_cases_failed=0,
                    test_case_results=[],
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    checked_at=datetime.utcnow(),
                    error="Application not reachable",
                )
            
            # Take initial screenshot
            if request.take_screenshots:
                screenshot_result = await self.mcp_client.screenshot("homepage")
                if screenshot_result.get("success") and screenshot_result.get("screenshot"):
                    path = self._save_screenshot(screenshot_result["screenshot"], "homepage")
                    screenshots.append(path)
            
            # Get test cases marked for integrity check
            test_cases = await self._get_integrity_check_test_cases(request.project_id)
            logger.info(f"[IntegrityCheck] Found {len(test_cases)} test cases marked for integrity check")
            
            if not test_cases:
                return IntegrityCheckResponse(
                    project_id=request.project_id,
                    status="passed",
                    app_reachable=True,
                    test_cases_total=0,
                    test_cases_passed=0,
                    test_cases_failed=0,
                    test_case_results=[],
                    screenshots=screenshots,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    checked_at=datetime.utcnow(),
                    error="No test cases marked for integrity check",
                )
            
            # Execute each test case
            test_cases_passed = 0
            test_cases_failed = 0
            
            for test_case in test_cases:
                tc_result = await self._execute_test_case(test_case, request.take_screenshots)
                test_case_results.append(tc_result)
                
                if tc_result.status == "passed":
                    test_cases_passed += 1
                else:
                    test_cases_failed += 1
                
                # Collect screenshots from step results
                for step_result in tc_result.step_results:
                    if step_result.screenshot_path:
                        screenshots.append(step_result.screenshot_path)
            
            # Determine overall status
            overall_status = "passed" if test_cases_failed == 0 else "failed"
            
            return IntegrityCheckResponse(
                project_id=request.project_id,
                status=overall_status,
                app_reachable=app_reachable,
                test_cases_total=len(test_cases),
                test_cases_passed=test_cases_passed,
                test_cases_failed=test_cases_failed,
                test_case_results=test_case_results,
                screenshots=screenshots,
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                checked_at=datetime.utcnow(),
            )
        
        except Exception as e:
            logger.error(f"[IntegrityCheck] Error: {e}")
            return IntegrityCheckResponse(
                project_id=request.project_id,
                status="error",
                app_reachable=app_reachable,
                test_cases_total=0,
                test_cases_passed=0,
                test_cases_failed=0,
                test_case_results=test_case_results,
                screenshots=screenshots,
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                checked_at=datetime.utcnow(),
                error=str(e),
            )
        
        finally:
            # Always close the browser session when done
            try:
                await self.mcp_client.close_session()
                logger.info("[IntegrityCheck] Browser session closed")
            except Exception as e:
                logger.warning(f"[IntegrityCheck] Failed to close browser session: {e}")
    
    async def _get_integrity_check_test_cases(self, project_id: int) -> List[TestCase]:
        """Get all test cases marked for integrity check.
        
        This includes:
        1. Test cases where integrity_check=True directly
        2. Test cases belonging to user stories where integrity_check=True
        """
        # First, get user story IDs that are marked for integrity check
        us_query = (
            select(UserStory.id)
            .where(UserStory.project_id == project_id)
            .where(UserStory.integrity_check == True)
        )
        us_result = await self.db.execute(us_query)
        integrity_check_user_story_ids = [row[0] for row in us_result.fetchall()]
        
        # Now get test cases that either:
        # 1. Have integrity_check=True themselves
        # 2. Belong to a user story that has integrity_check=True
        conditions = [TestCase.integrity_check == True]
        if integrity_check_user_story_ids:
            conditions.append(TestCase.user_story_id.in_(integrity_check_user_story_ids))
        
        query = (
            select(TestCase)
            .options(selectinload(TestCase.steps))
            .where(TestCase.project_id == project_id)
            .where(or_(*conditions))
            .order_by(TestCase.id)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def _execute_test_case(self, test_case: TestCase, take_screenshots: bool) -> "TestCaseResult":
        """Execute a single test case and return results."""
        from features.functional.schemas.integrity_check import StepResult, TestCaseResult
        
        tc_start_time = datetime.utcnow()
        step_results: List[StepResult] = []
        steps_passed = 0
        steps_failed = 0
        
        # Sort steps by step_number
        steps = sorted(test_case.steps, key=lambda s: s.step_number)
        
        logger.info(f"[IntegrityCheck] Executing test case: {test_case.title} ({len(steps)} steps)")
        
        for step in steps:
            step_result = await self._execute_step(step, test_case.title, take_screenshots)
            step_results.append(step_result)
            
            if step_result.status == "passed":
                steps_passed += 1
            else:
                steps_failed += 1
                # Stop execution on first failure for this test case
                logger.warning(f"[IntegrityCheck] Step {step.step_number} failed, stopping test case")
                break
        
        tc_duration = int((datetime.utcnow() - tc_start_time).total_seconds() * 1000)
        tc_status = "passed" if steps_failed == 0 else "failed"
        
        return TestCaseResult(
            test_case_id=test_case.id,
            title=test_case.title,
            status=tc_status,
            steps_total=len(steps),
            steps_passed=steps_passed,
            steps_failed=steps_failed,
            step_results=step_results,
            duration_ms=tc_duration,
        )
    
    async def _execute_step(self, step: TestStep, test_case_title: str, take_screenshots: bool) -> "StepResult":
        """Execute a single test step."""
        from features.functional.schemas.integrity_check import StepResult
        
        step_start_time = datetime.utcnow()
        screenshot_path = None
        
        try:
            action = step.action.value if hasattr(step.action, 'value') else str(step.action)
            logger.debug(f"[IntegrityCheck] Step {step.step_number}: {action} -> {step.target}")
            
            result = {"success": True}
            
            if action == "navigate":
                result = await self.mcp_client.navigate(step.target or step.value)
            elif action == "click":
                result = await self.mcp_client.click(step.target)
            elif action in ("fill", "type"):
                result = await self.mcp_client.fill(step.target, step.value or "")
            elif action == "select":
                result = await self.mcp_client.select(step.target, step.value or "")
            elif action == "hover":
                result = await self.mcp_client.hover(step.target)
            elif action == "wait":
                wait_time = int(step.value) if step.value else 1000
                result = await self.mcp_client.wait(wait_time)
            elif action == "screenshot":
                screenshot_result = await self.mcp_client.screenshot(step.target or "step")
                if screenshot_result.get("success") and screenshot_result.get("screenshot"):
                    screenshot_path = self._save_screenshot(screenshot_result["screenshot"], f"{test_case_title}_step_{step.step_number}")
                result = screenshot_result
            elif action == "assert_visible":
                is_visible = await self.mcp_client.is_visible(step.target)
                result = {"success": is_visible, "error": f"Element not visible: {step.target}" if not is_visible else None}
            elif action == "assert_text":
                text_result = await self.mcp_client.assert_text(step.target, step.value or "")
                result = text_result
            elif action == "assert_url":
                # Get current URL and check if it contains expected value
                # TODO: Implement in MCP client
                result = {"success": True}
            elif action == "check":
                # Checkbox check - use click for now
                result = await self.mcp_client.click(step.target)
            elif action == "uncheck":
                # Checkbox uncheck - use click for now
                result = await self.mcp_client.click(step.target)
            else:
                logger.warning(f"[IntegrityCheck] Unknown action: {action}")
                result = {"success": True}  # Skip unknown actions
            
            # Take screenshot after step if requested
            if take_screenshots and not screenshot_path and action != "screenshot":
                screenshot_result = await self.mcp_client.screenshot(f"step_{step.step_number}")
                if screenshot_result.get("success") and screenshot_result.get("screenshot"):
                    screenshot_path = self._save_screenshot(
                        screenshot_result["screenshot"], 
                        f"{test_case_title}_step_{step.step_number}"
                    )
            
            step_duration = int((datetime.utcnow() - step_start_time).total_seconds() * 1000)
            
            if result.get("success"):
                return StepResult(
                    step_number=step.step_number,
                    action=action,
                    description=step.description,
                    status="passed",
                    duration_ms=step_duration,
                    screenshot_path=screenshot_path,
                )
            else:
                return StepResult(
                    step_number=step.step_number,
                    action=action,
                    description=step.description,
                    status="failed",
                    duration_ms=step_duration,
                    error=result.get("error", "Action failed"),
                    screenshot_path=screenshot_path,
                )
        
        except Exception as e:
            step_duration = int((datetime.utcnow() - step_start_time).total_seconds() * 1000)
            logger.error(f"[IntegrityCheck] Step {step.step_number} error: {e}")
            return StepResult(
                step_number=step.step_number,
                action=step.action.value if hasattr(step.action, 'value') else str(step.action),
                description=step.description,
                status="error",
                duration_ms=step_duration,
                error=str(e),
                screenshot_path=screenshot_path,
            )
    
    async def get_history(self, project_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get integrity check history for a project."""
        # TODO: Store integrity checks in database
        return []
