"""
Test Step Generation Service - LLM-powered test step generation
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import json
import logging

from common.llm import get_llm_client
from features.functional.db.models.test_step import TestStep, TestStepAction
from features.functional.services.test_case_service import TestCaseService
from features.functional.core.llm_prompts.test_step_generation import TEST_STEP_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class TestStepGenerationService:
    """Service for AI-powered test step generation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_client()
        self.test_case_service = TestCaseService(db)
    
    def _normalize_action(self, action_str: str) -> str:
        """Normalize action string to valid enum value."""
        action = action_str.lower().strip()
        
        # Map common variants
        action_map = {
            "goto": "navigate",
            "go_to": "navigate",
            "type": "fill",
            "input": "fill",
            "enter": "fill",
            "press": "click",
            "tap": "click",
            "verify_text": "assert_text",
            "check_text": "assert_text",
            "verify_visible": "assert_visible",
            "check_visible": "assert_visible",
            "verify_url": "assert_url",
            "check_url": "assert_url",
            "expect_url": "assert_url",
            "expect_text": "assert_text",
            "expect_visible": "assert_visible",
            "assert": "assert_visible",
        }
        
        return action_map.get(action, action)
    
    async def generate_test_steps(self, test_case_id: int) -> Dict[str, Any]:
        """Generate test steps for a test case using LLM."""
        test_case = await self.test_case_service.get_by_id(test_case_id)
        if not test_case:
            return {"success": False, "error": "Test case not found"}
        
        try:
            # Prepare context
            context = f"""
Test Case: {test_case.title}
Description: {test_case.description or 'N/A'}
Preconditions: {test_case.preconditions or 'N/A'}
Category: {test_case.category.value}
"""
            
            # Call LLM
            print(f"[TestStepGeneration] Calling LLM for test_case_id={test_case_id}")
            import asyncio
            from common.llm.base import Message
            response = await asyncio.to_thread(
                self.llm.chat_sync,
                messages=[
                    Message(role="system", content=TEST_STEP_GENERATION_PROMPT),
                    Message(role="user", content=context)
                ],
                temperature=0.3,
            )
            print(f"[TestStepGeneration] LLM response received, length={len(response.content)} chars")
            
            # Parse response
            steps_data = self._parse_test_steps_response(response.content)
            
            # Valid actions
            valid_actions = {"navigate", "click", "type", "fill", "select", "check", 
                           "uncheck", "hover", "screenshot", "wait", "assert_text", 
                           "assert_visible", "assert_url", "assert_title", "custom"}
            
            # Create test steps
            created_steps = []
            for index, step_data in enumerate(steps_data, start=1):
                # Normalize and validate action
                raw_action = step_data.get("action", "custom")
                action_str = self._normalize_action(raw_action)
                if action_str not in valid_actions:
                    action_str = "custom"
                
                step = TestStep(
                    test_case_id=test_case_id,
                    step_number=index,
                    action=TestStepAction(action_str),
                    target=step_data.get("target"),
                    value=step_data.get("value"),
                    description=step_data.get("description"),
                    expected_result=step_data.get("expected_result"),
                )
                self.db.add(step)
                created_steps.append(step)
            
            await self.db.flush()
            
            return {
                "success": True,
                "steps_created": len(created_steps),
            }
        
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    async def regenerate_test_steps(self, test_case_id: int) -> Dict[str, Any]:
        """
        Regenerate test steps for a test case.
        
        This deletes existing steps and generates new ones.
        
        Args:
            test_case_id: The test case ID to regenerate steps for
            
        Returns:
            Dict with success status and steps created count
        """
        print(f"[TestStepGeneration] regenerate_test_steps called for test_case_id={test_case_id}")
        test_case = await self.test_case_service.get_by_id(test_case_id)
        if not test_case:
            return {"success": False, "error": "Test case not found"}
        
        try:
            # Delete existing steps
            await self.db.execute(
                delete(TestStep).where(TestStep.test_case_id == test_case_id)
            )
            
            # Generate new steps
            result = await self.generate_test_steps(test_case_id)
            
            if result.get("success"):
                await self.db.commit()
            
            return result
        
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _parse_test_steps_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into test step data."""
        # Try to extract JSON from response
        try:
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback: parse numbered steps
        steps = []
        current_step = {}
        
        for line in response.split('\n'):
            line = line.strip()
            if line and line[0].isdigit() and '.' in line[:3]:
                if current_step:
                    steps.append(current_step)
                current_step = {
                    "description": line.split('.', 1)[1].strip(),
                    "action": "custom",
                }
            elif line.startswith('Action:'):
                current_step["action"] = line[7:].strip().lower()
            elif line.startswith('Target:'):
                current_step["target"] = line[7:].strip()
            elif line.startswith('Expected:'):
                current_step["expected_result"] = line[9:].strip()
        
        if current_step:
            steps.append(current_step)
        
        return steps
