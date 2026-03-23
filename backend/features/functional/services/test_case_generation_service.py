"""
Test Case Generation Service - LLM-powered test case generation
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from common.llm import get_llm_client
from common.db.models.user_story import UserStory
from features.functional.db.models.test_case import TestCase, TestCasePriority, TestCaseCategory
from features.functional.schemas.test_case import GenerateTestCasesRequest
from features.functional.services.requirement_service import RequirementService
from features.functional.core.llm_prompts.test_case_generation import TEST_CASE_GENERATION_PROMPT


class TestCaseGenerationService:
    """Service for AI-powered test case generation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_client()
        self.requirement_service = RequirementService(db)
    
    async def generate_test_cases_from_requirement(
        self, requirement_id: int
    ) -> Dict[str, Any]:
        """Generate test cases from a requirement."""
        requirement = await self.requirement_service.get_by_id(requirement_id)
        if not requirement:
            return {"success": False, "error": "Requirement not found"}
        
        return await self._generate_test_cases(
            project_id=requirement.project_id,
            requirement_id=requirement.id,
            content=requirement.content or requirement.title,
        )
    
    async def generate_test_cases(
        self, request: GenerateTestCasesRequest
    ) -> Dict[str, Any]:
        """Generate test cases from various sources."""
        content_parts = []
        
        # From requirement
        if request.requirement_id:
            requirement = await self.requirement_service.get_by_id(request.requirement_id)
            if requirement:
                content_parts.append(f"Requirement: {requirement.title}\n{requirement.content}")
        
        # From Jira (legacy - user stories are now synced to DB)
        # If jira_keys are provided, they should be synced first via the sync flow
        if request.jira_keys:
            # TODO: Look up synced user stories by external_key instead of fetching from Jira
            pass
        
        # Custom prompt
        if request.custom_prompt:
            content_parts.append(f"Additional context: {request.custom_prompt}")
        
        if not content_parts:
            return {"success": False, "error": "No content to generate from"}
        
        return await self._generate_test_cases(
            project_id=request.project_id,
            requirement_id=request.requirement_id,
            content="\n\n".join(content_parts),
        )
    
    async def _generate_test_cases(
        self,
        project_id: int,
        requirement_id: Optional[int],
        content: str,
    ) -> Dict[str, Any]:
        """Internal method to generate test cases using LLM."""
        try:
            # Call LLM
            response = await self.llm.chat_with_system(
                system_prompt=TEST_CASE_GENERATION_PROMPT,
                user_prompt=content,
                temperature=0.3,
            )
            
            # Parse response
            test_cases_data = self._parse_test_cases_response(response.content)
            
            # Create test cases
            created_cases = []
            for tc_data in test_cases_data:
                test_case = TestCase(
                    project_id=project_id,
                    requirement_id=requirement_id,
                    title=tc_data.get("title", ""),
                    description=tc_data.get("description", ""),
                    preconditions=tc_data.get("preconditions", ""),
                    priority=TestCasePriority(tc_data.get("priority", "medium").lower()),
                    category=TestCaseCategory(tc_data.get("category", "regression").lower()),
                    is_generated=True,
                    generation_prompt=content[:1000],  # Store truncated prompt
                )
                self.db.add(test_case)
                await self.db.flush()
                created_cases.append(test_case)
            
            return {
                "success": True,
                "test_cases_created": len(created_cases),
                "test_case_ids": [tc.id for tc in created_cases],
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def generate_test_cases_from_user_story(
        self,
        user_story_id: int,
        include_steps: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate test cases from a user story.
        
        Args:
            user_story_id: ID of the user story to generate tests from
            include_steps: Whether to also generate test steps
        
        Returns:
            Dict with success status, test cases created, and details
        """
        # Import here to avoid circular dependency
        from features.functional.services.test_step_generation_service import TestStepGenerationService
        
        # Fetch user story
        result = await self.db.execute(
            select(UserStory).where(UserStory.id == user_story_id)
        )
        user_story = result.scalar_one_or_none()
        
        if not user_story:
            return {"success": False, "error": "User story not found"}
        
        # Build content for LLM
        content_parts = [
            f"User Story: {user_story.title}",
        ]
        
        if user_story.external_key:
            content_parts.append(f"ID: {user_story.external_key}")
        
        if user_story.description:
            content_parts.append(f"\nDescription:\n{user_story.description}")
        
        if user_story.acceptance_criteria:
            content_parts.append(f"\nAcceptance Criteria:\n{user_story.acceptance_criteria}")
        
        content_parts.append(f"\nItem Type: {user_story.item_type.value}")
        content_parts.append(f"Priority: {user_story.priority.value if user_story.priority else 'medium'}")
        
        if user_story.labels:
            content_parts.append(f"Labels: {', '.join(user_story.labels)}")
        
        content = "\n".join(content_parts)
        
        try:
            # Call LLM to generate test cases
            response = await self.llm.chat_with_system(
                system_prompt=TEST_CASE_GENERATION_PROMPT,
                user_prompt=content,
                temperature=0.3,
            )
            
            # Parse response
            test_cases_data = self._parse_test_cases_response(response.content)
            
            if not test_cases_data:
                return {
                    "success": False,
                    "error": "LLM did not return valid test cases",
                    "raw_response": response.content[:500],
                }
            
            # Create test cases
            created_cases = []
            for tc_data in test_cases_data:
                # Map priority safely
                priority_str = tc_data.get("priority", "medium").lower()
                if priority_str not in ["critical", "high", "medium", "low"]:
                    priority_str = "medium"
                
                # Map category safely
                category_str = tc_data.get("category", "regression").lower()
                if category_str not in ["smoke", "regression", "e2e", "integration", "sanity"]:
                    category_str = "regression"
                
                test_case = TestCase(
                    project_id=user_story.project_id,
                    user_story_id=user_story.id,
                    title=tc_data.get("title", f"Test for {user_story.title}"),
                    description=tc_data.get("description", ""),
                    preconditions=tc_data.get("preconditions", ""),
                    priority=TestCasePriority(priority_str),
                    category=TestCaseCategory(category_str),
                    is_generated=True,
                    generation_prompt=content[:1000],
                )
                self.db.add(test_case)
                await self.db.flush()
                created_cases.append(test_case)
                
                # Generate steps if requested
                if include_steps:
                    step_service = TestStepGenerationService(self.db)
                    await step_service.generate_test_steps(test_case.id)
            
            await self.db.commit()
            
            return {
                "success": True,
                "user_story_id": user_story_id,
                "user_story_key": user_story.external_key or f"US-{user_story.id}",
                "test_cases_created": len(created_cases),
                "test_cases": [
                    {
                        "id": tc.id,
                        "title": tc.title,
                        "priority": tc.priority.value,
                        "category": tc.category.value,
                    }
                    for tc in created_cases
                ],
            }
        
        except Exception as e:
            await self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _parse_test_cases_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into test case data."""
        # Try to extract JSON from response
        try:
            # Look for JSON array in response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback: parse structured text
        test_cases = []
        current_tc = {}
        
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('Title:'):
                if current_tc:
                    test_cases.append(current_tc)
                current_tc = {"title": line[6:].strip()}
            elif line.startswith('Description:'):
                current_tc["description"] = line[12:].strip()
            elif line.startswith('Priority:'):
                current_tc["priority"] = line[9:].strip().lower()
            elif line.startswith('Category:'):
                current_tc["category"] = line[9:].strip().lower()
        
        if current_tc:
            test_cases.append(current_tc)
        
        return test_cases
