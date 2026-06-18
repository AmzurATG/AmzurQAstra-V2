"""
Bulk Generation Service — orchestrates multi-story test case generation.

Per story pipeline:
  1. AcDecompositionService  → AcCondition list
  2. matrix_builder.build()  → CoverageMatrix
  3. TestCaseDesignService   → TestCaseSpec list
  4. coverage_validator      → CoverageReport + gaps
  5. TestCaseDesignService.fill_gaps() (if gaps found)
  6. Persist TestCase rows + TestStep generation (existing service)

Runs as a FastAPI BackgroundTask. Progress is polled via GenerationJobService.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.core.coverage import build_matrix, validate_coverage
from features.functional.db.models.generation_job import GenerationJob, GenerationJobProfile
from features.functional.db.models.test_case import (
    TestCase,
    TestCaseCategory,
    TestCasePriority,
    TestCaseScenarioType,
    TestCaseSource,
)
from features.functional.services.ac_decomposition_service import AcDecompositionService
from features.functional.services.generation_job_service import GenerationJobService
from features.functional.services.test_case_design_service import TestCaseDesignService
from features.functional.services.test_case_service import TestCaseService
from features.functional.services.ui_context_loader import format_inventory_for_prompt, get_latest_inventory
from common.db.models.user_story import UserStory
from sqlalchemy import select

logger = logging.getLogger(__name__)

_PRIORITY_MAP = {
    "critical": TestCasePriority.critical,
    "high": TestCasePriority.high,
    "medium": TestCasePriority.medium,
    "low": TestCasePriority.low,
}
_CATEGORY_MAP = {
    "smoke": TestCaseCategory.smoke,
    "regression": TestCaseCategory.regression,
    "e2e": TestCaseCategory.e2e,
    "integration": TestCaseCategory.integration,
    "sanity": TestCaseCategory.sanity,
}


def _story_context(story: UserStory) -> str:
    parts = [f"Title: {story.title}"]
    if story.description:
        parts.append(f"Description: {story.description[:800]}")
    if story.acceptance_criteria:
        parts.append(f"Acceptance Criteria:\n{story.acceptance_criteria[:1500]}")
    if story.priority:
        parts.append(f"Priority: {story.priority.value}")
    return "\n".join(parts)


async def _persist_cases(
    db: AsyncSession,
    story: UserStory,
    specs: List[Dict[str, Any]],
    include_steps: bool,
    inventory_meta: Optional[Dict[str, Any]] = None,
) -> List[int]:
    """Persist test case specs and optionally generate steps. Returns list of created IDs."""
    if not specs:
        return []

    tc_svc = TestCaseService(db)
    case_numbers = await tc_svc.allocate_case_numbers(story.project_id, len(specs))
    created_ids: List[int] = []

    for spec, case_number in zip(specs, case_numbers):
        tc = TestCase(
            project_id=story.project_id,
            case_number=case_number,
            user_story_id=story.id,
            title=spec.get("title", "Untitled"),
            description=spec.get("description", ""),
            preconditions=spec.get("preconditions", ""),
            priority=_PRIORITY_MAP.get(spec.get("priority", "medium"), TestCasePriority.medium),
            category=_CATEGORY_MAP.get(spec.get("category", "regression"), TestCaseCategory.regression),
            scenario_type=spec.get("scenario_type", TestCaseScenarioType.positive.value),
            ac_ref=spec.get("ac_ref"),
            is_generated=True,
            source=TestCaseSource.ai,
            generation_prompt=_story_context(story)[:1000],
            platform=inventory_meta.get("platform") if inventory_meta else None,
            actor_role=inventory_meta.get("actor_role") if inventory_meta else None,
            ui_page_ref=spec.get("ui_page_ref"),
        )
        db.add(tc)
        await db.flush()
        created_ids.append(tc.id)

    if include_steps:
        from features.functional.services.test_step_generation_service import TestStepGenerationService
        step_svc = TestStepGenerationService(db)
        for tc_id in created_ids:
            try:
                await step_svc.generate_test_steps(tc_id)
            except Exception as exc:
                logger.warning("Step generation failed tc_id=%s: %s", tc_id, exc)

    await db.commit()
    return created_ids


class BulkGenerationService:
    """
    Orchestrates end-to-end bulk test case generation for multiple user stories.

    Designed to run as a background task. All DB writes use the provided session.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.job_svc = GenerationJobService(db)
        self.ac_svc = AcDecompositionService(db)
        self.design_svc = TestCaseDesignService()

    async def run(self, job_id: int, include_steps: bool = True) -> None:
        """
        Main entry point called by the background task.
        Fetches job, iterates stories, updates progress, and marks job complete/failed.
        """
        job = await self.db.get(GenerationJob, job_id)
        if not job:
            logger.error("BulkGenerationService: job %s not found", job_id)
            return

        await self.job_svc.mark_running(job_id)
        story_ids: List[int] = list(job.story_ids or [])
        profile: str = job.profile or GenerationJobProfile.standard
        coverage_summary: List[Dict[str, Any]] = []

        inventory = await get_latest_inventory(self.db, job.project_id)
        inventory_text = format_inventory_for_prompt(inventory) if inventory else ""
        inventory_meta = (
            {"platform": inventory.platform, "actor_role": inventory.actor_role}
            if inventory
            else None
        )
        matrix_profile = profile
        if profile == GenerationJobProfile.production_web:
            matrix_profile = "production_web"

        for done_count, story_id in enumerate(story_ids):
            story = await self._fetch_story(story_id, job.project_id)
            if not story:
                logger.warning("BulkGenerationService: story %s not found, skipping", story_id)
                await self.job_svc.update_progress(job_id, done_count + 1, None)
                continue

            await self.job_svc.update_progress(job_id, done_count, story.title)

            story_report = await self._process_story(
                story, matrix_profile, include_steps, inventory, inventory_text, inventory_meta
            )
            coverage_summary.append(story_report)

        await self.job_svc.mark_completed(job_id, coverage_summary)

    async def _fetch_story(self, story_id: int, project_id: int):
        res = await self.db.execute(
            select(UserStory).where(
                UserStory.id == story_id,
                UserStory.project_id == project_id,
            )
        )
        return res.scalar_one_or_none()

    async def _process_story(
        self,
        story: UserStory,
        profile: str,
        include_steps: bool,
        inventory=None,
        inventory_text: str = "",
        inventory_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the full pipeline for a single story. Returns coverage summary dict."""
        try:
            conditions = await self.ac_svc.decompose(story.id)
            matrix = build_matrix(
                conditions,
                story.title,
                profile=profile,
                inventory=inventory,
            )
            context = _story_context(story)

            specs = await self.design_svc.generate_from_matrix(
                matrix, context, ui_inventory_text=inventory_text
            )

            report = validate_coverage(matrix, specs)

            if report.has_gaps:
                gap_specs = await self.design_svc.fill_gaps(report, context)
                specs.extend(gap_specs)

            created_ids = await _persist_cases(
                self.db, story, specs, include_steps, inventory_meta=inventory_meta
            )

            # Tally scenario type counts
            scenario_counts: Dict[str, int] = defaultdict(int)
            for spec in specs:
                scenario_counts[spec.get("scenario_type", "positive")] += 1

            return {
                "story_id": story.id,
                "story_title": story.title,
                "cases_created": len(created_ids),
                "coverage_percent": report.coverage_percent,
                "has_gaps": report.has_gaps,
                "scenario_counts": dict(scenario_counts),
            }

        except Exception as exc:
            logger.exception(
                "BulkGenerationService: story %s failed: %s", story.id, exc
            )
            return {
                "story_id": story.id,
                "story_title": story.title,
                "cases_created": 0,
                "coverage_percent": 0.0,
                "has_gaps": True,
                "error": str(exc),
            }
