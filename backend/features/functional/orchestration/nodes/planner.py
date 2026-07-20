"""Planner node: semantic grouping via reasoning LLM."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List

import config
from common.llm.factory import get_llm_client
from common.utils.logger import logger
from features.functional.core.llm_prompts.grouping import (
    GROUPING_SYSTEM_PROMPT,
    build_planner_user_prompt,
)
from features.functional.orchestration.state import GroupRow, OrchestrationState


def _parse_groups_json(text: str) -> List[GroupRow]:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start : end + 1]
    data = json.loads(raw)
    groups = data.get("groups") if isinstance(data, dict) else data
    if not isinstance(groups, list):
        raise ValueError("Planner output missing groups array")
    out: List[GroupRow] = []
    for i, g in enumerate(groups):
        if not isinstance(g, dict):
            continue
        gid = str(g.get("group_id") or f"G{i+1}")
        case_ids = [int(x) for x in (g.get("case_ids") or [])]
        out.append(
            GroupRow(
                group_id=gid,
                title=str(g.get("title") or gid),
                phase_order=list(g.get("phase_order") or ["authed"]),
                case_ids=case_ids,
                case_phases={str(k): str(v) for k, v in (g.get("case_phases") or {}).items()},
                merged_steps=dict(g.get("merged_steps") or {}),
                shared_login=bool(g.get("shared_login", False)),
                status="pending",
            )
        )
    return out


def _heuristic_groups(cases: List[Dict[str, Any]]) -> List[GroupRow]:
    """Fallback when LLM planner fails."""
    auth_markers = (
        "login", "log in", "signin", "sign in", "invalid", "password",
        "logout", "log out", "authentication", "unauthorized",
    )

    def _phase(case: Dict[str, Any]) -> str:
        hay = " ".join(
            [
                str(case.get("title") or ""),
                str(case.get("description") or ""),
                " ".join(str(s.get("description") or "") for s in (case.get("steps") or [])),
            ]
        ).lower()
        if any(m in hay for m in ("invalid", "wrong password", "incorrect", "empty field")):
            return "pre_auth"
        if any(m in hay for m in ("logout", "log out", "sign out")):
            return "teardown"
        if any(m in hay for m in auth_markers):
            return "authed"
        return "no_auth"

    authed: List[int] = []
    pre_auth: List[int] = []
    teardown: List[int] = []
    no_auth: List[int] = []
    case_phases: Dict[str, str] = {}
    for c in cases:
        cid = int(c["test_case_id"])
        ph = _phase(c)
        case_phases[str(cid)] = ph
        if ph == "pre_auth":
            pre_auth.append(cid)
        elif ph == "teardown":
            teardown.append(cid)
        elif ph == "no_auth":
            no_auth.append(cid)
        else:
            authed.append(cid)

    groups: List[GroupRow] = []
    if pre_auth or authed or teardown:
        all_ids = pre_auth + authed + teardown
        groups.append(
            GroupRow(
                group_id="G_heuristic_auth",
                title="Shared auth session",
                phase_order=["pre_auth", "login", "authed", "teardown"],
                case_ids=all_ids,
                case_phases=case_phases,
                merged_steps={
                    "login": {"description": "Login once with valid credentials", "run_once": True},
                    "logout": {"description": "Logout once at end", "run_once": True},
                },
                shared_login=True,
                status="pending",
            )
        )
    for c in cases:
        cid = int(c["test_case_id"])
        if case_phases.get(str(cid)) == "no_auth":
            groups.append(
                GroupRow(
                    group_id=f"G_noauth_{cid}",
                    title=str(c.get("title") or f"Case {cid}"),
                    phase_order=["no_auth"],
                    case_ids=[cid],
                    case_phases={str(cid): "no_auth"},
                    merged_steps={},
                    shared_login=False,
                    status="pending",
                )
            )
    return groups


async def _plan_chunk(
    chunk: List[Dict[str, Any]],
    app_url: str,
    chunk_idx: int,
) -> List[GroupRow]:
    if not chunk:
        return []
    model = getattr(config.settings, "ORCHESTRATION_REASONING_MODEL", "gpt-4o")
    client = get_llm_client(model=model)
    user_prompt = build_planner_user_prompt(chunk, app_url)
    try:
        resp = await client.chat_with_system(
            GROUPING_SYSTEM_PROMPT,
            user_prompt,
            model=model,
            temperature=0.1,
        )
        groups = _parse_groups_json(resp.content)
        for g in groups:
            g["group_id"] = f"{g.get('group_id', 'G')}_p{chunk_idx}"
        return groups
    except Exception as exc:
        logger.warning("[Planner] LLM chunk %s failed (%s); using heuristic", chunk_idx, exc)
        return _heuristic_groups(chunk)


async def planner_node(state: OrchestrationState) -> Dict[str, Any]:
    chunks = list(state.get("chunks") or [])
    app_url = state.get("app_url") or ""
    if not chunks:
        cases = list(state.get("cases") or [])
        chunks = [cases] if cases else []
    tasks = [_plan_chunk(chunk, app_url, i + 1) for i, chunk in enumerate(chunks)]
    partials = await asyncio.gather(*tasks)
    partial_group_tables = [list(p) for p in partials if p]
    return {
        "partial_group_tables": partial_group_tables,
        "status": "merging",
    }
