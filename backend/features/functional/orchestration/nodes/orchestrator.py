"""Orchestrator node: token sizing and planner fan-out."""
from __future__ import annotations

import math
from typing import Any, Dict, List

import tiktoken

import config
from features.functional.orchestration.state import OrchestrationState


def _estimate_tokens(cases: List[Dict[str, Any]]) -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        enc = None
    total = 0
    for c in cases:
        text = " ".join(
            [
                str(c.get("title") or ""),
                str(c.get("description") or ""),
                str(c.get("preconditions") or ""),
            ]
            + [str(s.get("description") or "") for s in (c.get("steps") or [])]
        )
        total += len(enc.encode(text)) if enc else max(1, len(text) // 4)
    return total


def _chunk_cases(
    cases: List[Dict[str, Any]],
    chunk_tokens: int,
) -> List[List[Dict[str, Any]]]:
    if not cases:
        return []
    chunks: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    current_tokens = 0
    for c in cases:
        ct = _estimate_tokens([c])
        if current and current_tokens + ct > chunk_tokens:
            chunks.append(current)
            current = [c]
            current_tokens = ct
        else:
            current.append(c)
            current_tokens += ct
    if current:
        chunks.append(current)
    return chunks


async def orchestrator_node(state: OrchestrationState) -> Dict[str, Any]:
    cases = list(state.get("cases") or [])
    total_tokens = _estimate_tokens(cases)
    chunk_target = int(
        getattr(config.settings, "ORCHESTRATION_PLANNER_CHUNK_TOKENS", 12000) or 12000
    )
    max_planners = int(getattr(config.settings, "ORCHESTRATION_MAX_PLANNERS", 4) or 4)
    chunks = _chunk_cases(cases, chunk_target)
    planner_count = max(1, min(max_planners, len(chunks) or 1))
    # Re-balance if we have fewer chunks than planners
    if len(chunks) < planner_count:
        planner_count = max(1, len(chunks))
    lane_count = int(getattr(config.settings, "ORCHESTRATION_LANE_COUNT", 6) or 6)
    return {
        "chunks": chunks,
        "planner_count": planner_count,
        "total_cases": len(cases),
        "lane_count": lane_count,
        "status": "planning",
        "partial_group_tables": [],
        "case_results": [],
        "failed_case_ids": [],
        "retry_results": [],
        "completed_count": 0,
    }
