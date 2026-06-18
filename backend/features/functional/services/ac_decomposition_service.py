"""
AC Decomposition Service — converts raw acceptance_criteria text into
structured AcCondition objects via deterministic parsing + optional LLM enrichment.

Uses deterministic ac_parser first (fast, free). LLM is called only when the
deterministic result has fewer than 2 conditions (likely complex/ambiguous text).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.user_story import UserStory
from common.llm import get_llm_client
from common.llm.base import Message
from features.functional.core.coverage.ac_parser import AcCondition, parse as parse_ac
from features.functional.core.llm_prompts.ac_decomposition import AC_DECOMPOSITION_PROMPT

logger = logging.getLogger(__name__)


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    raw = text.strip()
    m = re.search(r"```(?:json)?\s*(\[[\s\S]*\])\s*```", raw)
    if m:
        raw = m.group(1)
    else:
        m2 = re.search(r"(\[[\s\S]*\])", raw)
        if m2:
            raw = m2.group(1)
    return json.loads(raw)


def _llm_result_to_conditions(raw_list: List[Dict[str, Any]]) -> List[AcCondition]:
    """Convert LLM-returned dicts to AcCondition objects."""
    conditions: List[AcCondition] = []
    for i, item in enumerate(raw_list, start=1):
        ac_id = str(item.get("id", f"AC-{i}")).strip()
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        conditions.append(
            AcCondition(
                id=ac_id,
                text=text,
                has_validation_rule=bool(item.get("has_validation_rule", False)),
                has_numeric_boundary=bool(item.get("has_numeric_boundary", False)),
                input_fields=list(item.get("input_fields", [])),
                scenario_hints=list(item.get("scenario_hints", ["positive"])),
            )
        )
    return conditions


class AcDecompositionService:
    """
    Decomposes a user story's acceptance_criteria into structured AcConditions.

    Strategy:
      1. Run deterministic parser (fast, always).
      2. If result has < 2 conditions, call LLM with AC_DECOMPOSITION_PROMPT for enrichment.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm_client()

    async def decompose(self, user_story_id: int) -> List[AcCondition]:
        """
        Return structured conditions for the given user story.
        Falls back to a generic single condition when AC text is absent.
        """
        result = await self.db.execute(
            select(UserStory).where(UserStory.id == user_story_id)
        )
        story = result.scalar_one_or_none()
        if not story:
            logger.warning("AcDecompositionService: story %s not found", user_story_id)
            return []

        ac_text = (story.acceptance_criteria or "").strip()

        if not ac_text:
            # No AC text — create a single generic condition from the title
            return [
                AcCondition(
                    id="AC-1",
                    text=f"The system correctly implements: {story.title}",
                    has_validation_rule=False,
                    has_numeric_boundary=False,
                    scenario_hints=["positive"],
                )
            ]

        # Step 1: deterministic parse
        conditions = parse_ac(ac_text)

        # Step 2: LLM enrichment for short/complex AC
        if len(conditions) < 2 and len(ac_text) > 50:
            try:
                conditions = await self._enrich_with_llm(ac_text)
            except Exception as exc:
                logger.warning(
                    "AcDecompositionService: LLM enrichment failed for story %s: %s",
                    user_story_id,
                    exc,
                )
                # Fall back to deterministic result even if minimal

        return conditions or [
            AcCondition(
                id="AC-1",
                text=ac_text[:300],
                has_validation_rule=False,
                has_numeric_boundary=False,
                scenario_hints=["positive"],
            )
        ]

    async def _enrich_with_llm(self, ac_text: str) -> List[AcCondition]:
        response = await asyncio.to_thread(
            self.llm.chat_sync,
            messages=[
                Message(role="system", content=AC_DECOMPOSITION_PROMPT),
                Message(role="user", content=ac_text),
            ],
            temperature=0.1,
        )
        raw = _extract_json_array(response.content or "")
        return _llm_result_to_conditions(raw)
