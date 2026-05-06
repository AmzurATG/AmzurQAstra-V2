"""
Test Case Service
"""
import re
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sa_delete, or_, select, func
from sqlalchemy.orm import selectinload

from common.api.pagination import PaginationParams
from common.db.models.user_story import UserStory
from features.functional.db.models.requirement import Requirement
from features.functional.db.models.test_case import (
    TestCase,
    TestCaseCategory,
    TestCasePriority,
    TestCaseStatus,
    TestCaseSource,
)
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_step import TestStep
from features.functional.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestCaseResponse,
    UserStoryBrief,
)
from features.functional.schemas.test_case_import import (
    CsvImportErrorItem,
    TestCaseCsvImportResponse,
)
from features.functional.schemas.test_step import TestStepCreate, TestStepUpdate
from features.functional.services.test_case_csv_import import CaseDraft


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
                source=tc.source,
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
        payload = test_case_data.model_dump()
        test_case = TestCase(
            **payload,
            case_number=numbers[0],
            created_by=created_by,
            source=TestCaseSource.manual,
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

    async def _existing_case_external_keys(self, project_id: int) -> set[str]:
        r = await self.db.execute(
            select(TestCase.jira_key).where(
                TestCase.project_id == project_id,
                TestCase.jira_key.is_not(None),
            )
        )
        return {str(k).strip() for k in r.scalars().all() if k and str(k).strip()}

    async def _csv_import_foreign_key_issues(
        self, project_id: int, groups: Dict[str, CaseDraft]
    ) -> List[Tuple[str, CsvImportErrorItem]]:
        """(case_key, error) for missing requirement_id / user_story_id in this project."""

        out: List[Tuple[str, CsvImportErrorItem]] = []
        req_ids = {g.requirement_id for g in groups.values() if g.requirement_id}
        us_ids = {g.user_story_id for g in groups.values() if g.user_story_id}

        if req_ids:
            r = await self.db.execute(
                select(Requirement.id).where(
                    Requirement.project_id == project_id,
                    Requirement.id.in_(req_ids),
                )
            )
            found_req = set(r.scalars().all())
            missing_req = req_ids - found_req
            if missing_req:
                for ck, g in groups.items():
                    if g.requirement_id in missing_req:
                        row = min(g.source_rows) if g.source_rows else 0
                        out.append(
                            (
                                ck,
                                CsvImportErrorItem(
                                    row=row,
                                    column="requirement_id",
                                    message=f"requirement_id {g.requirement_id} not found in this project.",
                                ),
                            )
                        )

        if us_ids:
            r = await self.db.execute(
                select(UserStory.id).where(
                    UserStory.project_id == project_id,
                    UserStory.id.in_(us_ids),
                )
            )
            found_us = set(r.scalars().all())
            missing_us = us_ids - found_us
            if missing_us:
                for ck, g in groups.items():
                    if g.user_story_id in missing_us:
                        row = min(g.source_rows) if g.source_rows else 0
                        out.append(
                            (
                                ck,
                                CsvImportErrorItem(
                                    row=row,
                                    column="user_story_id",
                                    message=f"user_story_id {g.user_story_id} not found in this project.",
                                ),
                            )
                        )

        return out

    async def import_test_cases_from_csv(
        self,
        *,
        project_id: int,
        created_by: int,
        file_bytes: bytes,
        dry_run: bool = False,
        import_mode: str = "strict",
    ) -> TestCaseCsvImportResponse:
        """
        Import test cases and optional steps from a single UTF-8 CSV.

        import_mode:
        - strict: any validation problem aborts the whole import (no rows written).
        - permissive: row-level step issues are kept in `errors` but valid cases are written;
          duplicate external keys, invalid FKs, and constraint violations skip those cases only
          (see `warnings` and `skipped_case_groups`).
        """
        from features.functional.services import test_case_csv_import as tc_csv

        mode = (import_mode or "strict").strip().lower()
        if mode not in ("strict", "permissive"):
            return TestCaseCsvImportResponse(
                dry_run=dry_run,
                import_mode=import_mode,
                message="import_mode must be 'strict' or 'permissive'.",
                errors=[
                    CsvImportErrorItem(
                        row=0,
                        message="Invalid import_mode (use strict or permissive).",
                    )
                ],
            )

        warnings: List[CsvImportErrorItem] = []

        if len(file_bytes) > tc_csv.MAX_CSV_BYTES:
            return TestCaseCsvImportResponse(
                dry_run=dry_run,
                import_mode=mode,
                message="File too large.",
                errors=[
                    CsvImportErrorItem(
                        row=0,
                        message=f"Maximum upload size is {tc_csv.MAX_CSV_BYTES // (1024 * 1024)} MiB.",
                    )
                ],
            )

        text, dec_warn = tc_csv.decode_csv_bytes(file_bytes)
        warnings.extend(dec_warn)

        col_map, body, parse_fatal = tc_csv.parse_csv_to_rows(text)
        errors: List[CsvImportErrorItem] = list(parse_fatal)
        if errors and not body:
            return TestCaseCsvImportResponse(
                dry_run=dry_run,
                import_mode=mode,
                errors=errors,
                warnings=warnings,
                message="Could not parse CSV.",
            )

        groups, errors = tc_csv.build_case_groups(col_map, body, errors)
        tc_csv.validate_groups_non_empty(groups, errors)

        constraint_hits = tc_csv.collect_case_constraint_violations(groups)
        skip_keys: set[str] = set()

        if mode == "strict":
            if constraint_hits:
                errors.extend(item for _, item in constraint_hits)
            if errors:
                return TestCaseCsvImportResponse(
                    dry_run=dry_run,
                    import_mode=mode,
                    errors=errors,
                    warnings=warnings,
                    message="Import aborted (strict mode): fix validation errors and try again.",
                )
        else:
            for ck, item in constraint_hits:
                warnings.append(item)
                skip_keys.add(ck)

        existing_ext = await self._existing_case_external_keys(project_id)
        dup_hits: List[Tuple[str, CsvImportErrorItem]] = []
        for ck, g in groups.items():
            if ck in existing_ext:
                row = min(g.source_rows) if g.source_rows else 0
                dup_hits.append(
                    (
                        ck,
                        CsvImportErrorItem(
                            row=row,
                            column="case_key",
                            message=f"case_key {ck!r} already exists on a test case in this project (external id).",
                        ),
                    )
                )

        fk_hits = await self._csv_import_foreign_key_issues(project_id, groups)

        if mode == "strict":
            if dup_hits:
                errors.extend(item for _, item in dup_hits)
            if fk_hits:
                errors.extend(item for _, item in fk_hits)
            if errors:
                return TestCaseCsvImportResponse(
                    dry_run=dry_run,
                    import_mode=mode,
                    errors=errors,
                    warnings=warnings,
                    message="Import aborted (strict mode): fix validation errors and try again.",
                )
        else:
            for ck, item in dup_hits:
                warnings.append(item)
                skip_keys.add(ck)
            for ck, item in fk_hits:
                warnings.append(item)
                skip_keys.add(ck)

        eligible = {k: g for k, g in groups.items() if k not in skip_keys}
        skipped = len(groups) - len(eligible)
        step_total = sum(len(g.steps) for g in eligible.values())
        case_total = len(eligible)

        if case_total == 0:
            return TestCaseCsvImportResponse(
                dry_run=dry_run,
                import_mode=mode,
                created_cases=0,
                created_steps=0,
                skipped_case_groups=skipped,
                errors=errors,
                warnings=warnings,
                message="No test cases to import (all skipped or file empty).",
            )

        if dry_run:
            return TestCaseCsvImportResponse(
                dry_run=True,
                import_mode=mode,
                created_cases=case_total,
                created_steps=step_total,
                skipped_case_groups=skipped,
                errors=errors,
                warnings=warnings,
                message=f"Dry run: would create {case_total} case(s) and {step_total} step(s).",
            )

        sorted_keys = sorted(eligible.keys())
        numbers = await self.allocate_case_numbers(project_id, len(sorted_keys))
        orm_cases: List[TestCase] = []
        key_to_orm: Dict[str, TestCase] = {}

        for i, ck in enumerate(sorted_keys):
            g = eligible[ck]
            tc = TestCase(
                project_id=project_id,
                case_number=numbers[i],
                title=(g.title or ck).strip()[:500],
                description=g.description or None,
                preconditions=g.preconditions or None,
                priority=g.priority,
                category=g.category,
                status=g.status,
                tags=(g.tags.strip() if g.tags else None) or None,
                requirement_id=g.requirement_id,
                user_story_id=g.user_story_id,
                jira_key=ck[:50],
                is_automated=True,
                is_generated=False,
                source=TestCaseSource.csv,
                created_by=created_by,
            )
            orm_cases.append(tc)
            key_to_orm[ck] = tc

        self.db.add_all(orm_cases)
        await self.db.flush()

        step_batch: List[TestStep] = []
        STEP_CHUNK = 400
        created_steps = 0

        for ck in sorted_keys:
            g = eligible[ck]
            tc = key_to_orm[ck]
            for st in g.steps:
                assert st.step_number is not None
                step_batch.append(
                    TestStep(
                        test_case_id=tc.id,
                        step_number=st.step_number,
                        action=st.action,
                        target=(st.target[:500] if st.target else None),
                        value=st.value,
                        description=st.description,
                        expected_result=st.expected_result,
                    )
                )
                if len(step_batch) >= STEP_CHUNK:
                    self.db.add_all(step_batch)
                    await self.db.flush()
                    created_steps += len(step_batch)
                    step_batch = []

        if step_batch:
            self.db.add_all(step_batch)
            await self.db.flush()
            created_steps += len(step_batch)

        return TestCaseCsvImportResponse(
            dry_run=False,
            import_mode=mode,
            created_cases=case_total,
            created_steps=created_steps,
            skipped_case_groups=skipped,
            errors=errors,
            warnings=warnings,
            message=f"Imported {case_total} case(s) and {created_steps} step(s).",
        )
