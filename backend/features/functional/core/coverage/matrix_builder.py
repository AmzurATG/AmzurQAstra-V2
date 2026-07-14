"""
Coverage matrix builder — expands AcConditions into required test-case rows.

Profiles (approximate row budgets):
  light          ~5
  standard       ~10
  comprehensive  ~20
  production_web comprehensive + UI smoke rows from inventory
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence

from features.functional.core.coverage.ac_parser import AcCondition

_PROFILE_TARGETS = {
    "light": 5,
    "standard": 10,
    "comprehensive": 20,
    "production_web": 20,
}


@dataclass
class MatrixRow:
    """One required test case slot in the coverage matrix."""

    ac_ref: str
    scenario_type: str
    instruction: str


@dataclass
class CoverageMatrix:
    """Ordered set of required coverage rows for a user story."""

    rows: List[MatrixRow] = field(default_factory=list)
    story_title: str = ""
    profile: str = "standard"

    def total(self) -> int:
        return len(self.rows)


def _scenarios_for(condition: AcCondition) -> List[str]:
    """Derive scenario types from condition flags and hints."""
    scenarios: List[str] = []
    hints = {h.lower() for h in (condition.scenario_hints or [])}

    scenarios.append("positive")
    if condition.has_validation_rule or "negative" in hints:
        scenarios.append("negative")
    if condition.has_numeric_boundary or "boundary" in hints:
        scenarios.append("boundary")
    if "edge" in hints:
        scenarios.append("edge")

    # Deduplicate while preserving order
    seen = set()
    ordered: List[str] = []
    for s in scenarios:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def _instruction(condition: AcCondition, scenario: str) -> str:
    base = condition.text
    if scenario == "positive":
        return f"Verify happy path: {base}"
    if scenario == "negative":
        return f"Verify rejection/error path: {base}"
    if scenario == "boundary":
        return f"Verify numeric/limit boundary: {base}"
    if scenario == "edge":
        return f"Verify edge/unusual case: {base}"
    return base


def _expand_conditions(conditions: Sequence[AcCondition]) -> List[MatrixRow]:
    rows: List[MatrixRow] = []
    for cond in conditions:
        for scenario in _scenarios_for(cond):
            rows.append(
                MatrixRow(
                    ac_ref=cond.id,
                    scenario_type=scenario,
                    instruction=_instruction(cond, scenario),
                )
            )
    return rows


def _trim_or_pad(rows: List[MatrixRow], target: int, conditions: Sequence[AcCondition]) -> List[MatrixRow]:
    """Trim or pad rows toward the profile target size."""
    if target <= 0:
        return rows

    if len(rows) > target:
        # Prefer keeping positive + negative; drop edge then boundary extras first
        priority = {"positive": 0, "negative": 1, "boundary": 2, "edge": 3, "ui_smoke": 4}
        ranked = sorted(
            enumerate(rows),
            key=lambda ir: (priority.get(ir[1].scenario_type, 9), ir[0]),
        )
        keep_idx = sorted(i for i, _ in ranked[:target])
        return [rows[i] for i in keep_idx]

    if len(rows) < target and conditions:
        # Pad with extra positive variants cycling through conditions
        i = 0
        while len(rows) < target:
            cond = conditions[i % len(conditions)]
            rows.append(
                MatrixRow(
                    ac_ref=cond.id,
                    scenario_type="positive",
                    instruction=f"Additional coverage variant: {cond.text}",
                )
            )
            i += 1
    elif len(rows) < target:
        while len(rows) < target:
            rows.append(
                MatrixRow(
                    ac_ref="AC-1",
                    scenario_type="positive",
                    instruction="Verify core story behavior",
                )
            )
    return rows


def _ui_rows(inventory: Any, max_pages: int = 8) -> List[MatrixRow]:
    """Build ui_smoke rows from a UiInventory-like object."""
    pages = getattr(inventory, "pages", None) or []
    rows: List[MatrixRow] = []
    for page in pages[:max_pages]:
        name = getattr(page, "name", None) or "Unknown page"
        rows.append(
            MatrixRow(
                ac_ref="UI",
                scenario_type="ui_smoke",
                instruction=f"Smoke-check page '{name}' is reachable and key controls are visible",
            )
        )
    return rows


def build(
    conditions: Sequence[AcCondition],
    story_title: str,
    profile: str = "standard",
    inventory: Optional[Any] = None,
) -> CoverageMatrix:
    """
    Build a CoverageMatrix for the given conditions and generation profile.
    """
    profile_key = (profile or "standard").lower()
    target = _PROFILE_TARGETS.get(profile_key, _PROFILE_TARGETS["standard"])

    conds = list(conditions) if conditions else [
        AcCondition(id="AC-1", text=f"The system correctly implements: {story_title}")
    ]
    rows = _expand_conditions(conds)
    rows = _trim_or_pad(rows, target, conds)

    if profile_key == "production_web" and inventory is not None:
        rows.extend(_ui_rows(inventory))

    return CoverageMatrix(rows=rows, story_title=story_title or "", profile=profile_key)


# Public alias used by BulkGenerationService
build_matrix = build
