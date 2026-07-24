"""Deterministic report aggregator — nest sub-groups under parent themes.

Not an LLM agent: pure rollup for stable, auditable output.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _group_stats(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    return {
        "passed": sum(1 for c in cases if c.get("status") == "passed"),
        "failed": sum(1 for c in cases if c.get("status") == "failed"),
        "error": sum(1 for c in cases if c.get("status") == "error"),
        "total": len(cases),
    }


def aggregate_groups_by_parent(
    groups: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Nest groups that share parent_group_id under a theme node.

    Groups without a parent stay top-level. Parent title is derived from the
    first child's title prefix before ' · ' when possible.
    """
    if not groups:
        return []

    children_by_parent: Dict[str, List[Dict[str, Any]]] = {}
    roots: List[Dict[str, Any]] = []
    standalone: List[Dict[str, Any]] = []

    for g in groups:
        parent = g.get("parent_group_id")
        if parent:
            children_by_parent.setdefault(str(parent), []).append(g)
        else:
            standalone.append(g)

    # Parents that only exist as parent_group_id (no row of their own)
    emitted_parents: set[str] = set()
    for parent_id, children in children_by_parent.items():
        # Prefer an explicit parent row if present in standalone
        parent_row = next(
            (s for s in standalone if s.get("group_id") == parent_id),
            None,
        )
        if parent_row:
            standalone = [s for s in standalone if s.get("group_id") != parent_id]

        title = (parent_row or {}).get("title") or parent_id
        # Derive theme name from "Theme · Facet"
        for ch in children:
            t = str(ch.get("title") or "")
            if " · " in t:
                title = t.split(" · ", 1)[0].strip() or title
                break

        all_cases: List[Dict[str, Any]] = []
        for ch in children:
            all_cases.extend(ch.get("cases") or [])
        stats = _group_stats(all_cases)
        roots.append(
            {
                "group_id": parent_id,
                "parent_group_id": None,
                "title": title,
                "is_theme": True,
                "shared_login": bool((parent_row or children[0]).get("shared_login")),
                "phase_order": (parent_row or children[0]).get("phase_order") or [],
                "case_ids": [c.get("test_case_id") for c in all_cases],
                "cases": all_cases,
                "sub_groups": [
                    {
                        **ch,
                        "is_theme": False,
                        **_group_stats(ch.get("cases") or []),
                    }
                    for ch in children
                ],
                **stats,
            }
        )
        emitted_parents.add(parent_id)

    for s in standalone:
        cases = s.get("cases") or []
        roots.append(
            {
                **s,
                "is_theme": False,
                "sub_groups": [],
                **_group_stats(cases),
            }
        )

    return roots
