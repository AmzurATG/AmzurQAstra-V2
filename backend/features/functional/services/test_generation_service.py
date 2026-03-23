"""
Test Generation Service - Backward compatibility shim

This module re-exports from the split services for backward compatibility.
New code should import directly from:
- test_case_generation_service.TestCaseGenerationService
- test_step_generation_service.TestStepGenerationService
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

# Re-export for backward compatibility
from features.functional.services.test_case_generation_service import TestCaseGenerationService
from features.functional.services.test_step_generation_service import TestStepGenerationService


class TestGenerationService:
    """
    Backward-compatible unified service that delegates to split services.
    
    Deprecated: Use TestCaseGenerationService or TestStepGenerationService directly.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._case_service = TestCaseGenerationService(db)
        self._step_service = TestStepGenerationService(db)
    
    async def generate_test_cases_from_requirement(
        self, requirement_id: int
    ) -> Dict[str, Any]:
        """Generate test cases from a requirement."""
        return await self._case_service.generate_test_cases_from_requirement(requirement_id)
    
    async def generate_test_cases(self, request) -> Dict[str, Any]:
        """Generate test cases from various sources."""
        return await self._case_service.generate_test_cases(request)
    
    async def generate_test_cases_from_user_story(
        self,
        user_story_id: int,
        include_steps: bool = True,
    ) -> Dict[str, Any]:
        """Generate test cases from a user story."""
        return await self._case_service.generate_test_cases_from_user_story(
            user_story_id, include_steps
        )
    
    async def generate_test_steps(self, test_case_id: int) -> Dict[str, Any]:
        """Generate test steps for a test case using LLM."""
        return await self._step_service.generate_test_steps(test_case_id)
