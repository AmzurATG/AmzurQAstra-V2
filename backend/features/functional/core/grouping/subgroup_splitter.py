"""Deterministic subgroup splitter."""
from __future__ import annotations

import string
from typing import Any, Dict, List, Sequence

from features.functional.core.grouping.side_effect_classifier import (
    SideEffectClass,
    classify_role_facet,
    classify_side_effect,
    facet_label,
    max_cases_for,
)

GroupDict = Dict[str, Any]


def _suffix(i: int) -> str:
    letters = string.ascii_lowercase
    if i < 26:
        return letters[i]
    return _suffix(i // 26 - 1) + letters[i % 26]


def split_group(group: GroupDict, cases: Sequence[Dict[str, Any]]) -> List[GroupDict]:
    case_ids = [int(x) for x in (group.get("case_ids") or [])]
    if not case_ids:
        return []
    cmap = {int(c["test_case_id"]): c for c in cases if c.get("test_case_id") is not None}
    parent_id = str(group.get("group_id") or "G")
    parent_title = str(group.get("title") or parent_id)
    case_phases = dict(group.get("case_phases") or {})
    buckets: Dict[tuple, List[int]] = {}
    side_by: Dict[int, SideEffectClass] = {}
    for cid in case_ids:
        case = cmap.get(cid) or {"test_case_id": cid, "title": "", "steps": []}
        side = classify_side_effect(case)
        role = classify_role_facet(case)
        side_by[cid] = side
        buckets.setdefault((side.value, role or ""), []).append(cid)

    dominant = SideEffectClass.MUTATING
    classes = set(side_by.values())
    for pref in (SideEffectClass.DESTRUCTIVE, SideEffectClass.MUTATING, SideEffectClass.AUTH, SideEffectClass.READ_ONLY):
        if pref in classes:
            dominant = pref
            break
    if len(case_ids) <= max_cases_for(dominant) and len(buckets) <= 1:
        row = dict(group)
        row["parent_group_id"] = group.get("parent_group_id")
        row["side_effect"] = dominant.value
        return [row]

    out: List[GroupDict] = []
    seq = 0
    order = {SideEffectClass.DESTRUCTIVE.value: 0, SideEffectClass.MUTATING.value: 1, SideEffectClass.AUTH.value: 2, SideEffectClass.READ_ONLY.value: 3}
    for side_val, role in sorted(buckets.keys(), key=lambda k: (order.get(k[0], 9), k[1])):
        side = SideEffectClass(side_val)
        cap = max_cases_for(side)
        ids = sorted(buckets[(side_val, role)])
        for chunk_idx in range(0, len(ids), cap):
            chunk = ids[chunk_idx : chunk_idx + cap]
            facet = facet_label(side, role or None, chunk_idx // cap)
            gid = f"{parent_id}_{_suffix(seq)}"
            seq += 1
            out.append({
                "group_id": gid,
                "parent_group_id": parent_id,
                "title": f"{parent_title} · {facet}",
                "phase_order": list(group.get("phase_order") or ["authed"]),
                "case_ids": chunk,
                "case_phases": {str(k): str(v) for k, v in case_phases.items() if int(k) in chunk},
                "merged_steps": dict(group.get("merged_steps") or {}),
                "shared_login": bool(group.get("shared_login", False)),
                "status": "pending",
                "side_effect": side.value,
                "facet": facet,
            })
    return out or [dict(group)]


def split_group_table(groups: Sequence[GroupDict], cases: Sequence[Dict[str, Any]]) -> List[GroupDict]:
    seen: set[int] = set()
    result: List[GroupDict] = []
    for g in groups:
        for sub in split_group(g, cases):
            unique = [c for c in (int(x) for x in (sub.get("case_ids") or [])) if c not in seen]
            if not unique:
                continue
            seen.update(unique)
            row = dict(sub)
            row["case_ids"] = unique
            result.append(row)
    return result
