"""
Plan Safety Validator — deterministic post-LLM rules that override dangerous
grouping decisions before execution starts.

The LLM is great at understanding flow dependencies but may occasionally put a
negative-auth test into a shared session (where the browser is already logged
in, making the negative test meaningless).  These rules catch that.

This module is pure Python with no I/O — easy to unit test.
"""
from __future__ import annotations

import dataclasses
from typing import Any, Dict, List

from common.utils.logger import logger
from features.functional.core.execution.execution_plan import (
    ExecutionGroup,
    GroupedRunPlan,
    PlannedCase,
)

# Keywords in title/description/preconditions that indicate a negative auth test.
_NEGATIVE_AUTH_PHRASES = frozenset(
    [
        "invalid password",
        "wrong password",
        "incorrect password",
        "bad password",
        "invalid credentials",
        "wrong credentials",
        "incorrect credentials",
        "invalid email",
        "wrong email",
        "incorrect email",
        "invalid login",
        "login fail",
        "failed login",
        "authentication fail",
        "auth fail",
        "unauthorized",
        "unauthenticated",
        "locked account",
        "suspended account",
        "account locked",
        "non-existent user",
        "nonexistent user",
        "unregistered user",
        "without registering",
        "no account",
    ]
)

# Phrases that signal the case needs a fresh/clean browser state.
_FRESH_STATE_PHRASES = frozenset(
    [
        "clear cookies",
        "fresh session",
        "logged out",
        "not logged in",
        "before login",
        "without login",
        "unauthenticated state",
        "clean browser",
        "private browsing",
        "incognito",
    ]
)


def _is_negative_auth(tc_meta: Dict[str, Any]) -> bool:
    """Return True if the case is a negative authentication test."""
    if tc_meta.get("scenario_type", "positive") == "negative":
        blob = " ".join(
            [
                tc_meta.get("title", ""),
                tc_meta.get("preconditions", ""),
                tc_meta.get("description", ""),
                tc_meta.get("first_step", ""),
            ]
        ).lower()
        if any(p in blob for p in _NEGATIVE_AUTH_PHRASES):
            return True
    return False


def _needs_fresh_state(tc_meta: Dict[str, Any]) -> bool:
    """Return True if the case explicitly needs a clean browser state."""
    blob = " ".join(
        [
            tc_meta.get("title", ""),
            tc_meta.get("preconditions", ""),
            tc_meta.get("description", ""),
        ]
    ).lower()
    return any(p in blob for p in _FRESH_STATE_PHRASES)


def _build_meta_index(tc_summaries: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Index tc_summaries by tc_id for O(1) lookup during validation."""
    return {tc["tc_id"]: tc for tc in tc_summaries}


def validate_and_fix(
    plan: GroupedRunPlan,
    tc_summaries: List[Dict[str, Any]],
) -> GroupedRunPlan:
    """
    Apply safety rules to the LLM-generated plan and return a corrected plan.

    Rules applied (in order):
    1. Negative-auth cases in a shared group → move to isolated lane.
    2. Fresh-state cases in a shared group → move to isolated lane.
    3. Browser lane numbers are clamped to [1, MAX_LANES].
    4. Ensure every tc_id appears exactly once (detect LLM duplicates/omissions).

    Parameters
    ----------
    plan:
        The raw plan from GroupingAgent.
    tc_summaries:
        The same compact dicts passed to GroupingAgent (used for metadata lookup).

    Returns
    -------
    A corrected GroupedRunPlan.
    """
    from features.functional.core.execution.planner_agent import MAX_LANES

    meta = _build_meta_index(tc_summaries)
    all_planned_ids: set[int] = set()
    overflows: List[PlannedCase] = []  # Cases evicted from shared groups
    corrected_groups: List[ExecutionGroup] = []
    next_isolated_lane = _pick_lightest_lane(plan, MAX_LANES)

    for group in plan.groups:
        safe_cases: List[PlannedCase] = []

        for planned in group.ordered_cases:
            tc_id = planned.tc_id
            if tc_id in all_planned_ids:
                logger.warning(
                    f"[PlanSafetyValidator] Duplicate tc_id={tc_id} in plan — skipping copy."
                )
                continue
            all_planned_ids.add(tc_id)

            tc_meta = meta.get(tc_id, {})

            if group.is_shared and (
                _is_negative_auth(tc_meta) or _needs_fresh_state(tc_meta)
            ):
                logger.info(
                    f"[PlanSafetyValidator] tc_id={tc_id} moved to isolated — "
                    "negative/fresh-state case cannot share a session."
                )
                overflows.append(planned)
            else:
                safe_cases.append(planned)

        if safe_cases:
            clamped_lane = max(1, min(MAX_LANES, group.browser_lane))
            # Filter merged_steps to only reference tc_ids still in safe_cases.
            # Evicted cases are gone from this group, so prune their satisfies entries
            # to avoid the EvaluatorAgent wasting time looking them up.
            remaining_tc_ids = {c.tc_id for c in safe_cases}
            pruned_merged_steps = []
            for ms in group.merged_steps:
                filtered_satisfies = [
                    s for s in ms.satisfies if s.get("tc_id") in remaining_tc_ids
                ]
                if filtered_satisfies:
                    pruned_merged_steps.append(
                        dataclasses.replace(ms, satisfies=filtered_satisfies)
                    )
            corrected_groups.append(
                ExecutionGroup(
                    group_id=group.group_id,
                    label=group.label,
                    session_type=group.session_type if safe_cases else "isolated",
                    browser_lane=clamped_lane,
                    reset_url=group.reset_url,
                    ordered_cases=safe_cases,
                    merged_steps=pruned_merged_steps,
                )
            )

    # Evicted cases → each gets its own isolated mini-group.
    for planned in overflows:
        tc_meta = meta.get(planned.tc_id, {})
        title = tc_meta.get("title", f"Case {planned.tc_id}")[:40]
        corrected_groups.append(
            ExecutionGroup(
                group_id=f"ISO_{planned.tc_id}",
                label=f"[Isolated] {title}",
                session_type="isolated",
                browser_lane=next_isolated_lane,
                reset_url=_find_reset_url(plan, planned.tc_id),
                ordered_cases=[
                    PlannedCase(
                        tc_id=planned.tc_id,
                        order=1,
                        reset_before=None,
                        reason="Safety override: negative/fresh-state case isolated.",
                    )
                ],
            )
        )

    # Check for any tc_ids missing from the plan entirely (LLM omission bug).
    all_input_ids = {tc["tc_id"] for tc in tc_summaries}
    missing = all_input_ids - all_planned_ids
    if missing:
        logger.warning(
            f"[PlanSafetyValidator] {len(missing)} tc_id(s) missing from LLM plan "
            f"— adding as isolated: {sorted(missing)}"
        )
        for tc_id in sorted(missing):
            tc_meta = meta.get(tc_id, {})
            title = tc_meta.get("title", f"Case {tc_id}")[:40]
            corrected_groups.append(
                ExecutionGroup(
                    group_id=f"MISS_{tc_id}",
                    label=f"[Isolated] {title}",
                    session_type="isolated",
                    browser_lane=next_isolated_lane,
                    reset_url=plan.groups[0].reset_url if plan.groups else "",
                    ordered_cases=[
                        PlannedCase(
                            tc_id=tc_id,
                            order=1,
                            reset_before=None,
                            reason="Added by safety validator — LLM omitted this case.",
                        )
                    ],
                )
            )

    total = sum(len(g.ordered_cases) for g in corrected_groups)
    return GroupedRunPlan(
        strategy=plan.strategy,
        groups=corrected_groups,
        total_cases=total,
        parallelism=plan.parallelism,
    )


def _pick_lightest_lane(plan: GroupedRunPlan, max_lanes: int) -> int:
    """Return the lane with the fewest currently planned cases."""
    lane_counts: Dict[int, int] = {i: 0 for i in range(1, max_lanes + 1)}
    for g in plan.groups:
        lane = max(1, min(max_lanes, g.browser_lane))
        lane_counts[lane] = lane_counts.get(lane, 0) + len(g.ordered_cases)
    return min(lane_counts, key=lane_counts.get)  # type: ignore[arg-type]


def _find_reset_url(plan: GroupedRunPlan, tc_id: int) -> str:
    """Find the reset_url of whichever group originally had this case."""
    for g in plan.groups:
        for c in g.ordered_cases:
            if c.tc_id == tc_id:
                return g.reset_url
    return plan.groups[0].reset_url if plan.groups else ""
