"""
Test Case Design Service — coverage-matrix-driven LLM test case generation.

Generates test cases from a CoverageMatrix spec, then fills gaps identified
by the CoverageValidator. Produces TestCaseSpec dicts (not persisted here —
the orchestrator handles persistence).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List

from common.llm import get_llm_client
from common.llm.base import Message
from features.functional.core.coverage.coverage_validator import CoverageReport
from features.functional.core.coverage.matrix_builder import CoverageMatrix
from features.functional.core.llm_prompts.test_case_design import (
    GAP_FILL_PROMPT,
    MATRIX_EXPANSION_PROMPT,
    MATRIX_EXPANSION_WITH_UI_PROMPT,
)

logger = logging.getLogger(__name__)

_VALID_PRIORITIES = {"critical", "high", "medium", "low"}
_VALID_CATEGORIES = {"smoke", "regression", "e2e", "integration", "sanity"}
_VALID_SCENARIO_TYPES = {"positive", "negative", "boundary", "edge", "ui_smoke"}


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


def _coerce_case(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate a single LLM-generated test case dict."""
    priority = str(raw.get("priority", "medium")).lower()
    category = str(raw.get("category", "regression")).lower()
    scenario_type = str(raw.get("scenario_type", "positive")).lower()
    return {
        "title": str(raw.get("title", "")).strip()[:500] or "Untitled test case",
        "description": str(raw.get("description", "")).strip(),
        "preconditions": str(raw.get("preconditions", "")).strip(),
        "priority": priority if priority in _VALID_PRIORITIES else "medium",
        "category": category if category in _VALID_CATEGORIES else "regression",
        "scenario_type": scenario_type if scenario_type in _VALID_SCENARIO_TYPES else "positive",
        "ac_ref": str(raw.get("ac_ref", "")).strip()[:20] or None,
        "test_data": raw.get("test_data") or {},
        "expected_behavior": str(raw.get("expected_behavior", "")).strip(),
    }


class TestCaseDesignService:
    """
    Generates test case specs from a CoverageMatrix using LLM.

    Responsibility: LLM in → structured specs out. No DB, no persistence.
    """

    def __init__(self) -> None:
        self.llm = get_llm_client()

    def _build_user_message(
        self, matrix: CoverageMatrix, story_context: str, ui_inventory_text: str = ""
    ) -> str:
        matrix_lines = "\n".join(
            f"  Row {i + 1}: ac_ref={row.ac_ref}, scenario_type={row.scenario_type}, "
            f"instruction={row.instruction}"
            for i, row in enumerate(matrix.rows)
        )
        ui_section = f"\n\n=== UI INVENTORY ===\n{ui_inventory_text}" if ui_inventory_text else ""
        return (
            f"=== USER STORY ===\n{story_context}\n\n"
            f"=== COVERAGE MATRIX ({matrix.total()} rows) ===\n{matrix_lines}"
            f"{ui_section}"
        )

    async def generate_from_matrix(
        self,
        matrix: CoverageMatrix,
        story_context: str,
        ui_inventory_text: str = "",
        max_retries: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Call LLM with the coverage matrix and return a list of test case spec dicts.
        Retries once on JSON parse failure or wrong count.
        """
        user_msg = self._build_user_message(matrix, story_context, ui_inventory_text)
        system_prompt = MATRIX_EXPANSION_WITH_UI_PROMPT if ui_inventory_text else MATRIX_EXPANSION_PROMPT
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 2):
            try:
                response = await asyncio.to_thread(
                    self.llm.chat_sync,
                    messages=[
                        Message(role="system", content=system_prompt),
                        Message(role="user", content=user_msg),
                    ],
                    temperature=0.2,
                )
                raw_list = _extract_json_array(response.content or "")
                cases = [_coerce_case(r) for r in raw_list]
                if cases:
                    return cases
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "TestCaseDesignService: attempt %d/%d failed: %s",
                    attempt, max_retries + 1, exc,
                )

        logger.error("TestCaseDesignService: all attempts failed: %s", last_error)
        return []

    async def fill_gaps(
        self,
        report: CoverageReport,
        story_context: str,
    ) -> List[Dict[str, Any]]:
        """Generate additional cases to fill coverage gaps."""
        open_gaps = [g for g in report.gaps if g.missing_count > 0]
        if not open_gaps:
            return []

        gaps_payload = [
            {
                "ac_ref": g.ac_ref,
                "scenario_type": g.scenario_type,
                "required_count": g.missing_count,
            }
            for g in open_gaps
        ]
        prompt = GAP_FILL_PROMPT.format(
            gaps_json=json.dumps(gaps_payload, indent=2),
            story_context=story_context,
        )
        try:
            response = await asyncio.to_thread(
                self.llm.chat_sync,
                messages=[
                    Message(role="system", content=prompt),
                    Message(role="user", content="Generate the gap-fill test cases now."),
                ],
                temperature=0.25,
            )
            raw_list = _extract_json_array(response.content or "")
            return [_coerce_case(r) for r in raw_list]
        except Exception as exc:
            logger.warning("TestCaseDesignService: gap-fill failed: %s", exc)
            return []
