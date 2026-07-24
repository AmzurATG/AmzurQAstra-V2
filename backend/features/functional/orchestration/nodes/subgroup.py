"""Subgroup node: split oversized semantic groups after planner merge."""
from __future__ import annotations

from typing import Any, Dict

from common.utils.logger import logger
from features.functional.core.grouping.subgroup_splitter import split_group_table
from features.functional.orchestration.state import OrchestrationState


async def subgroup_node(state: OrchestrationState) -> Dict[str, Any]:
    groups = list(state.get("group_table") or [])
    cases = list(state.get("cases") or [])
    before = len(groups)
    before_cases = sum(len(g.get("case_ids") or []) for g in groups)
    split = split_group_table(groups, cases)
    after_cases = sum(len(g.get("case_ids") or []) for g in split)
    logger.info(
        "[Subgroup] %s planner groups → %s sub-groups (%s→%s cases)",
        before, len(split), before_cases, after_cases,
    )
    return {
        "group_table": split,
        "status": "dispatching",
    }
