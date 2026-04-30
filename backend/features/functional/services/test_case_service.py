"""
Test Case Service
"""
import re
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sa_delete, or_, select, func
from sqlalchemy.orm import selectinload

from common.api.pagination import PaginationParams
from common.db.models.user_story import UserStory
from features.functional.db.models.test_case import TestCase, TestCaseCategory, TestCasePriority, TestCaseStatus
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_step import TestStep
from features.functional.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    UserStoryBrief,
)
from features.functional.schemas.test_step import TestStepCreate, TestStepUpdate


class TestCaseService:
    """Service for test case operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, test_case_id: int) -> Optional[TestCase]:
        """Get test case by ID."""
        result = await self.db.execute(
            select(TestCase).where(TestCase.id == test_case_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id_with_steps(self, test_case_id: int) -> Optional[TestCase]:
        """Get test case by ID with all steps and user story."""
        result = await self.db.execute(
            select(TestCase)
            .options(selectinload(TestCase.steps))
            .options(selectinload(TestCase.user_story))
            .where(TestCase.id == test_case_id)
        )
        return result.scalar_one_or_none()

    async def allocate_case_numbers(self, project_id: int, count: int) -> List[int]:
        """Return the next `count` per-project case numbers (1-based), without inserting rows."""
        if count <= 0:
            return []
        result = await self.db.execute(
            select(func.coalesce(func.max(TestCase.case_number), 0)).where(
                TestCase.project_id == project_id
            )
        )
        start = int(result.scalar() or 0) + 1
        return list(range(start, start + count))
    
    async def get_list(
        self,
        project_id: int,
        requirement_id: Optional[int] = None,
        user_story_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
        include_steps: bool = False,
    ) -> Tuple[List[TestCaseResponse], int]:
        """Get list of test cases with filters."""
        query = (
            select(TestCase)
            .options(selectinload(TestCase.user_story))
            .where(TestCase.project_id == project_id)
        )
        if include_steps:
            query = query.options(selectinload(TestCase.steps))
        count_query = select(func.count(TestCase.id)).where(
            TestCase.project_id == project_id
        )
        
        # Apply filters
        if requirement_id:
            query = query.where(TestCase.requirement_id == requirement_id)
            count_query = count_query.where(TestCase.requirement_id == requirement_id)
        
        if user_story_id:
            query = query.where(TestCase.user_story_id == user_story_id)
            count_query = count_query.where(TestCase.user_story_id == user_story_id)
        
        if status:
            try:
                status_enum = TestCaseStatus(status)
            except ValueError:
                status_enum = status
            query = query.where(TestCase.status == status_enum)
            count_query = count_query.where(TestCase.status == status_enum)
        
        if priority:
            try:
                pri_enum = TestCasePriority(priority)
            except ValueError:
                pri_enum = priority
            query = query.where(TestCase.priority == pri_enum)
            count_query = count_query.where(TestCase.priority == pri_enum)
        
        if category:
            try:
                cat_enum = TestCaseCategory(category)
            except ValueError:
                cat_enum = category
            query = query.where(TestCase.category == cat_enum)
            count_query = count_query.where(TestCase.category == cat_enum)
        
        if search:
            raw = (search or "").strip()
            if raw:
                term = f"%{raw}%"
                query = query.outerjoin(
                    UserStory, TestCase.user_story_id == UserStory.id
                )
                count_query = count_query.outerjoin(
                    UserStory, TestCase.user_story_id == UserStory.id
                )

                or_conditions = [
                    TestCase.title.ilike(term),
                    UserStory.external_key.ilike(term),
                ]
                # US-42 / us-42 / US42 / us 42 — same display label as the UI
                us_match = re.match(r"^us\s*-?\s*(\d+)\s*$", raw, re.IGNORECASE)
                if us_match:
                    or_conditions.append(UserStory.id == int(us_match.group(1)))
                elif raw.isdigit():
                    or_conditions.append(UserStory.id == int(raw))

                query = query.where(or_(*or_conditions))
                count_query = count_query.where(or_(*or_conditions))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.order_by(TestCase.case_number.asc(), TestCase.id.asc())
        
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        
        result = await self.db.execute(query)
        test_cases = result.scalars().all()
        
        # Get steps count for all test cases in one query to avoid lazy loading
        tc_ids = [tc.id for tc in test_cases]
        counts_map = {}
        if tc_ids:
            counts_query = (
                select(TestStep.test_case_id, func.count(TestStep.id))
                .where(TestStep.test_case_id.in_(tc_ids))
                .group_by(TestStep.test_case_id)
            )
            counts_result = await self.db.execute(counts_query)
            counts_map = {row[0]: row[1] for row in counts_result.all()}
        
        # Convert to response with user_story info
        responses = []
        for tc in test_cases:
            user_story_brief = None
            if tc.user_story:
                user_story_brief = UserStoryBrief(
                    id=tc.user_story.id,
                    external_key=tc.user_story.external_key,
                    title=tc.user_story.title,
                    item_type=tc.user_story.item_type.value,
                )
            
            responses.append(TestCaseResponse(
                id=tc.id,
                case_number=tc.case_number,
                project_id=tc.project_id,
                requirement_id=tc.requirement_id,
                user_story_id=tc.user_story_id,
                user_story=user_story_brief,
                title=tc.title,
                description=tc.description,
                preconditions=tc.preconditions,
                priority=tc.priority,
                category=tc.category,
                status=tc.status,
                tags=tc.tags,
                is_automated=tc.is_automated,
                is_generated=tc.is_generated,
                integrity_check=tc.integrity_check,
                jira_key=tc.jira_key,
                created_by=tc.created_by,
                created_at=tc.created_at,
                updated_at=tc.updated_at,
                steps_count=counts_map.get(tc.id, 0),
            ))
        
        return responses, total
    
    async def create(self, test_case_data: TestCaseCreate, created_by: int) -> TestCase:
        """Create a new test case."""
        numbers = await self.allocate_case_numbers(test_case_data.project_id, 1)
        test_case = TestCase(
            **test_case_data.model_dump(),
            case_number=numbers[0],
            created_by=created_by,
        )
        self.db.add(test_case)
        await self.db.flush()
        # Re-fetch with relationships for proper serialization
        return await self.get_by_id_with_steps(test_case.id)
    
    async def update(
        self, test_case_id: int, test_case_data: TestCaseUpdate
    ) -> Optional[TestCase]:
        """Update a test case."""
        test_case = await self.get_by_id(test_case_id)
        if not test_case:
            return None
        
        update_data = test_case_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(test_case, field, value)
        
        await self.db.flush()
        # Re-fetch with relationships for proper serialization
        return await self.get_by_id_with_steps(test_case_id)
    
    async def delete(self, test_case_id: int) -> bool:
        """Delete a test case, its steps (ORM cascade), and linked test run results."""
        test_case = await self.get_by_id(test_case_id)
        if not test_case:
            return False

        # test_results references test_cases without ON DELETE CASCADE — remove results first
        await self.db.execute(
            sa_delete(TestResult).where(TestResult.test_case_id == test_case_id)
        )
        await self.db.delete(test_case)
        await self.db.flush()
        return True
    
    # Test Step operations
    async def get_steps(self, test_case_id: int) -> List[TestStep]:
        """Get all steps for a test case."""
        result = await self.db.execute(
            select(TestStep)
            .where(TestStep.test_case_id == test_case_id)
            .order_by(TestStep.step_number)
        )
        return list(result.scalars().all())
    
    async def add_step(self, step_data: TestStepCreate) -> TestStep:
        """Add a step to a test case."""
        # Get next step number if not provided
        if step_data.step_number is None:
            result = await self.db.execute(
                select(func.max(TestStep.step_number))
                .where(TestStep.test_case_id == step_data.test_case_id)
            )
            max_step = result.scalar() or 0
            step_number = max_step + 1
        else:
            step_number = step_data.step_number
        
        step = TestStep(
            **step_data.model_dump(exclude={"step_number"}),
            step_number=step_number,
        )
        self.db.add(step)
        await self.db.flush()
        await self.db.refresh(step)
        return step
    
    async def update_step(
        self, step_id: int, step_data: TestStepUpdate
    ) -> Optional[TestStep]:
        """Update a test step."""
        result = await self.db.execute(
            select(TestStep).where(TestStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if not step:
            return None
        
        update_data = step_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(step, field, value)
        
        await self.db.flush()
        await self.db.refresh(step)
        return step
    
    async def delete_step(self, step_id: int) -> bool:
        """Delete a test step."""
        result = await self.db.execute(
            select(TestStep).where(TestStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if not step:
            return False
        
        await self.db.delete(step)
        await self.db.flush()
        return True
    
    async def reorder_steps(
        self, test_case_id: int, step_ids: List[int]
    ) -> List[TestStep]:
        """Reorder test steps."""
        steps = await self.get_steps(test_case_id)
        step_map = {step.id: step for step in steps}
        
        for index, step_id in enumerate(step_ids, start=1):
            if step_id in step_map:
                step_map[step_id].step_number = index
        
        await self.db.flush()
        return await self.get_steps(test_case_id)
