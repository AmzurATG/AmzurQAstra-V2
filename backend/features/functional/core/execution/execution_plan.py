"""
Execution Plan — data structures that represent a grouped parallel run plan.

Produced by the PlannerAgent (one-time LLM call) and persisted in
TestRun.config so every subsequent poll/retry uses the same deterministic plan.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PlannedCase:
    """A single test case within an execution group."""

    tc_id: int
    order: int
    # URL to navigate to before starting this case (shared-session resets).
    # None means start from wherever the previous case left off.
    reset_before: Optional[str]
    # LLM reasoning — logged for transparency
    reason: str


@dataclass
class MergedStep:
    """
    A deduplicated step that satisfies one or more original test-case steps.

    When a merged step covers the login step across 10 cases, executing it
    once marks step_number=1 as passed for all 10 cases.
    """

    merged_step_number: int
    action: str
    description: str
    target: Optional[str] = None
    value: Optional[str] = None
    expected_result: Optional[str] = None
    # List of {tc_id, step_number} that this merged step satisfies.
    satisfies: List[Dict[str, int]] = field(default_factory=list)


# Maps "group_id:merged_step_number" → list of {tc_id, step_number} originals.
# Used by EvaluatorAgent to fan execution results back to each TestResult.
StepOriginMap = Dict[str, List[Dict[str, int]]]


@dataclass
class ExecutionGroup:
    """A cluster of test cases that run in one browser session."""

    group_id: str
    label: str
    # "shared"   → one browser, login once, run all cases sequentially inside.
    # "isolated" → each case gets its own fresh browser (default for negative tests).
    session_type: str
    # Which parallel browser lane (1..MAX_LANES) this group runs on.
    browser_lane: int
    # Landing URL used to establish a known starting state for the group.
    reset_url: str
    ordered_cases: List[PlannedCase] = field(default_factory=list)
    # Deduplicated step script for this group (built by PlannerAgent).
    # Empty for isolated groups (each case runs its own steps via TestCaseRunner).
    merged_steps: List[MergedStep] = field(default_factory=list)

    @property
    def is_shared(self) -> bool:
        return self.session_type == "shared"

    @property
    def tc_ids(self) -> List[int]:
        return [c.tc_id for c in self.ordered_cases]


@dataclass
class GroupedRunPlan:
    """The full execution plan for a test run."""

    strategy: str  # "grouped_parallel" | "sequential"
    groups: List[ExecutionGroup] = field(default_factory=list)
    total_cases: int = 0

    # How many browser lanes to run in parallel (capped at MAX_LANES).
    parallelism: int = 3

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for storage in TestRun.config JSONB."""
        return {
            "strategy": self.strategy,
            "parallelism": self.parallelism,
            "total_cases": self.total_cases,
            "groups": [
                {
                    "group_id": g.group_id,
                    "label": g.label,
                    "session_type": g.session_type,
                    "browser_lane": g.browser_lane,
                    "reset_url": g.reset_url,
                    "merged_steps": [
                        {
                            "merged_step_number": ms.merged_step_number,
                            "action": ms.action,
                            "description": ms.description,
                            "target": ms.target,
                            "value": ms.value,
                            "expected_result": ms.expected_result,
                            "satisfies": ms.satisfies,
                        }
                        for ms in g.merged_steps
                    ],
                    "ordered_cases": [
                        {
                            "tc_id": c.tc_id,
                            "order": c.order,
                            "reset_before": c.reset_before,
                            "reason": c.reason,
                        }
                        for c in g.ordered_cases
                    ],
                }
                for g in self.groups
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GroupedRunPlan":
        """Deserialize from the JSONB dict stored in TestRun.config."""
        groups: List[ExecutionGroup] = []
        for gd in data.get("groups", []):
            cases = [
                PlannedCase(
                    tc_id=c["tc_id"],
                    order=c["order"],
                    reset_before=c.get("reset_before"),
                    reason=c.get("reason", ""),
                )
                for c in gd.get("ordered_cases", [])
            ]
            merged: List[MergedStep] = [
                MergedStep(
                    merged_step_number=ms["merged_step_number"],
                    action=ms["action"],
                    description=ms["description"],
                    target=ms.get("target"),
                    value=ms.get("value"),
                    expected_result=ms.get("expected_result"),
                    satisfies=ms.get("satisfies", []),
                )
                for ms in gd.get("merged_steps", [])
            ]
            groups.append(
                ExecutionGroup(
                    group_id=gd["group_id"],
                    label=gd["label"],
                    session_type=gd.get("session_type", "isolated"),
                    browser_lane=gd.get("browser_lane", 1),
                    reset_url=gd.get("reset_url", ""),
                    ordered_cases=cases,
                    merged_steps=merged,
                )
            )
        return cls(
            strategy=data.get("strategy", "grouped_parallel"),
            groups=groups,
            total_cases=data.get("total_cases", 0),
            parallelism=data.get("parallelism", 3),
        )

    def build_step_origin_map(self) -> StepOriginMap:
        """
        Build the StepOriginMap from all groups' merged_steps.

        Key: "{group_id}:{merged_step_number}"
        Value: list of {tc_id, step_number} originals this merged step satisfies.
        """
        origin_map: StepOriginMap = {}
        for g in self.groups:
            for ms in g.merged_steps:
                key = f"{g.group_id}:{ms.merged_step_number}"
                origin_map[key] = ms.satisfies
        return origin_map
