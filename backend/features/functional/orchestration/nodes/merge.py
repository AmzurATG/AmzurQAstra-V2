"""Merge node: combine planner outputs into final group table."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from features.functional.orchestration.state import GroupRow, OrchestrationState


async def merge_node(state: OrchestrationState) -> Dict[str, Any]:
    partials = list(state.get("partial_group_tables") or [])
    seen_cases: Set[int] = set()
    merged: List[GroupRow] = []
    seq = 0
    for partial in partials:
        for g in partial:
            case_ids = [int(x) for x in (g.get("case_ids") or [])]
            unique = [c for c in case_ids if c not in seen_cases]
            if not unique:
                continue
            for c in unique:
                seen_cases.add(c)
            seq += 1
            merged.append(
                GroupRow(
                    group_id=str(g.get("group_id") or f"G{seq}"),
                    title=str(g.get("title") or f"Group {seq}"),
                    phase_order=list(g.get("phase_order") or ["authed"]),
                    case_ids=unique,
                    case_phases={
                        str(k): str(v)
                        for k, v in (g.get("case_phases") or {}).items()
                        if int(k) in unique
                    },
                    merged_steps=dict(g.get("merged_steps") or {}),
                    shared_login=bool(g.get("shared_login", False)),
                    status="pending",
                )
            )
    # Any cases not assigned get solo groups
    all_cases = state.get("cases") or []
    for c in all_cases:
        cid = int(c["test_case_id"])
        if cid not in seen_cases:
            seq += 1
            merged.append(
                GroupRow(
                    group_id=f"G_solo_{cid}",
                    title=str(c.get("title") or f"Case {cid}"),
                    phase_order=["authed"],
                    case_ids=[cid],
                    case_phases={str(cid): "authed"},
                    merged_steps={},
                    shared_login=False,
                    status="pending",
                )
            )
            seen_cases.add(cid)
    return {
        "group_table": merged,
        "status": "dispatching",
    }
