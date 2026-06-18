"""
Planner Agent — one LLM call that:

1. Receives ALL test cases with ALL their steps.
2. Detects duplicate/equivalent steps across cases (same intent — login, navigate, etc.).
3. Produces a merged step script per group (fewer steps, login once).
4. Assigns groups to parallel browser lanes.
5. Returns a GroupedRunPlan (with merged_steps on each shared group) and a
   StepOriginMap for fan-out attribution after execution.

Replaces the old GroupingAgent which only saw title + first step.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from common.llm import get_llm_client
from common.llm.base import Message
from common.utils.logger import logger
from features.functional.core.execution.execution_plan import (
    ExecutionGroup,
    GroupedRunPlan,
    MergedStep,
    PlannedCase,
    StepOriginMap,
)

MAX_LANES = 4  # Hard cap on parallel browser windows

_PLANNER_SYSTEM_PROMPT = """\
You are an expert QA test orchestration planner with deep understanding of web application flows.

Your job: given a list of test cases with full step definitions, create an intelligent execution plan that:
1. Groups cases that can share a browser session (login once, run multiple).
2. Merges duplicate/equivalent steps across cases in a group into a single merged script.
3. Assigns groups to parallel browser lanes for maximum speed.

## GROUPING RULES

1. **Shared session** (`session_type: "shared"`):
   - Cases that all require valid authenticated access.
   - Cases that test different features but share setup (login, navigate to app).
   - Group by feature area — dashboard cases together, settings cases together, etc.
   - Within a shared group, order cases logically (setup first, then verification, logout last).

2. **Isolated session** (`session_type: "isolated"`):
   - Negative authentication cases (wrong password, invalid email, locked account).
   - Cases where preconditions require fresh/clean browser state.
   - Cases with scenario_type = "negative" that test auth/login flows.
   - Cases that say "clear cookies", "fresh session", "logged out".

3. **Step Merging** (CRITICAL — this is the core value):
   - Within a shared group, find steps with the same ACTION and INTENT across cases.
   - Common duplicates: "Navigate to app URL", "Login with valid credentials", "Open dashboard".
   - Create ONE merged step that runs once and satisfies the equivalent step in every case.
   - Each merged step has a `satisfies` list: [{tc_id, step_number}] for every original step it covers.
   - Case-specific steps that only apply to one case get their own merged step with satisfies=[{that case only}].
   - The merged script runs top-to-bottom in one browser: shared prefix steps first, then case-specific segments.

4. **Browser lanes** (parallel execution):
   - Assign groups to lanes 1 through {max_lanes} (inclusive).
   - Different groups on different lanes run simultaneously.
   - Balance load: similar case counts per lane.

## STEP MERGING EXAMPLE

If TC-10 has: [Step 1: Login, Step 2: Open Dashboard, Step 3: Verify widget]
And TC-11 has: [Step 1: Login, Step 2: Go to Reports, Step 3: Export CSV]

Merged script for the group:
  MergedStep 1: "Login valid user" → satisfies: TC-10 step 1, TC-11 step 1
  MergedStep 2: "Open Dashboard → Verify widget" → satisfies: TC-10 steps 2-3
  MergedStep 3: "Go to Reports → Export CSV" → satisfies: TC-11 steps 2-3

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no explanation):

{{
  "strategy": "grouped_parallel",
  "parallelism": <number 1-{max_lanes}>,
  "groups": [
    {{
      "group_id": "G1",
      "label": "<short human-readable name>",
      "session_type": "shared",
      "browser_lane": 1,
      "reset_url": "<app_url or specific path>",
      "merged_steps": [
        {{
          "merged_step_number": 1,
          "action": "<action type e.g. navigate, fill, click>",
          "description": "<what this step does>",
          "target": "<CSS selector or URL or null>",
          "value": "<input value or null>",
          "expected_result": "<what to verify or null>",
          "satisfies": [
            {{"tc_id": <integer>, "step_number": <integer>}},
            {{"tc_id": <integer>, "step_number": <integer>}}
          ]
        }}
      ],
      "ordered_cases": [
        {{
          "tc_id": <integer>,
          "order": 1,
          "reset_before": "<URL or null>",
          "reason": "<one sentence why this case is in this group>"
        }}
      ]
    }}
  ]
}}

For isolated groups, `merged_steps` should be [] (the runner uses original case steps directly).
""".replace("{max_lanes}", str(MAX_LANES))


def _build_full_case_payload(tc: Dict[str, Any]) -> str:
    """Build detailed per-case text including all steps for the planner prompt."""
    parts = [
        f"TC_ID: {tc['tc_id']}",
        f"Title: {tc['title']}",
        f"Scenario Type: {tc.get('scenario_type', 'positive')}",
        f"Priority: {tc.get('priority', 'medium')}",
        f"Tags: {tc.get('tags', '') or 'none'}",
    ]
    if tc.get("preconditions"):
        parts.append(f"Preconditions: {tc['preconditions'][:300]}")
    if tc.get("description"):
        parts.append(f"Description: {tc['description'][:200]}")

    steps = tc.get("steps", [])
    if steps:
        parts.append("Steps:")
        for s in steps:
            step_parts = [f"  Step {s['step_number']}: [{s.get('action', 'custom')}]"]
            if s.get("description"):
                step_parts.append(s["description"])
            if s.get("target"):
                step_parts.append(f"→ Target: {s['target']}")
            if s.get("value"):
                step_parts.append(f"→ Value: {s['value']}")
            if s.get("expected_result"):
                step_parts.append(f"→ Expect: {s['expected_result']}")
            parts.append(" | ".join(step_parts))

    return "\n".join(parts)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Pull JSON from LLM output, tolerating markdown fences."""
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    brace = text.find("{")
    if brace == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[brace:], start=brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _parse_plan(data: Dict[str, Any], app_url: str) -> GroupedRunPlan:
    """Convert raw LLM JSON dict into a typed GroupedRunPlan with MergedSteps."""
    groups: List[ExecutionGroup] = []

    for gd in data.get("groups", []):
        # Parse ordered_cases
        cases: List[PlannedCase] = []
        for c in gd.get("ordered_cases", []):
            tc_id = c.get("tc_id")
            if tc_id is None:
                continue
            cases.append(
                PlannedCase(
                    tc_id=int(tc_id),
                    order=int(c.get("order", 1)),
                    reset_before=c.get("reset_before") or None,
                    reason=str(c.get("reason", "")),
                )
            )
        if not cases:
            continue

        # Parse merged_steps
        merged: List[MergedStep] = []
        for ms in gd.get("merged_steps", []):
            msn = ms.get("merged_step_number")
            if msn is None:
                continue
            satisfies = []
            for s in ms.get("satisfies", []):
                tc_id_s = s.get("tc_id")
                step_num = s.get("step_number")
                if tc_id_s is not None and step_num is not None:
                    satisfies.append({"tc_id": int(tc_id_s), "step_number": int(step_num)})
            merged.append(
                MergedStep(
                    merged_step_number=int(msn),
                    action=str(ms.get("action", "custom")),
                    description=str(ms.get("description", "")),
                    target=ms.get("target") or None,
                    value=ms.get("value") or None,
                    expected_result=ms.get("expected_result") or None,
                    satisfies=satisfies,
                )
            )

        lane = max(1, min(MAX_LANES, int(gd.get("browser_lane", 1))))
        groups.append(
            ExecutionGroup(
                group_id=str(gd.get("group_id", f"G{len(groups)+1}")),
                label=str(gd.get("label", f"Group {len(groups)+1}")),
                session_type=str(gd.get("session_type", "isolated")),
                browser_lane=lane,
                reset_url=str(gd.get("reset_url", "") or app_url),
                ordered_cases=cases,
                merged_steps=merged,
            )
        )

    parallelism = max(1, min(MAX_LANES, int(data.get("parallelism", 3))))
    total = sum(len(g.ordered_cases) for g in groups)
    return GroupedRunPlan(
        strategy=str(data.get("strategy", "grouped_parallel")),
        groups=groups,
        total_cases=total,
        parallelism=parallelism,
    )


def _fallback_sequential_plan(
    tc_full_payloads: List[Dict[str, Any]], app_url: str
) -> GroupedRunPlan:
    """Return one isolated group per case — safe fallback when LLM fails."""
    groups: List[ExecutionGroup] = []
    for i, tc in enumerate(tc_full_payloads):
        groups.append(
            ExecutionGroup(
                group_id=f"G{i+1}",
                label=tc.get("title", f"Case {tc['tc_id']}")[:50],
                session_type="isolated",
                browser_lane=1,
                reset_url=app_url,
                ordered_cases=[
                    PlannedCase(
                        tc_id=tc["tc_id"],
                        order=1,
                        reset_before=None,
                        reason="Fallback: sequential isolated execution",
                    )
                ],
                merged_steps=[],
            )
        )
    return GroupedRunPlan(
        strategy="sequential",
        groups=groups,
        total_cases=len(tc_full_payloads),
        parallelism=1,
    )


async def build_execution_plan(
    tc_full_payloads: List[Dict[str, Any]],
    app_url: str,
    max_retries: int = 2,
) -> Tuple[GroupedRunPlan, StepOriginMap]:
    """
    Call the LLM once to plan test case grouping with full step merging.

    Parameters
    ----------
    tc_full_payloads:
        List of dicts with keys:
        tc_id, title, scenario_type, priority, tags, preconditions, description, steps.
        Each `steps` is a list of step dicts (step_number, action, target, value, description,
        expected_result).
    app_url:
        The application base URL.
    max_retries:
        How many times to retry if the LLM returns unparseable output.

    Returns
    -------
    (GroupedRunPlan, StepOriginMap) — never raises; falls back to sequential isolated on failure.
    """
    if not tc_full_payloads:
        plan = GroupedRunPlan(strategy="sequential", groups=[], total_cases=0, parallelism=1)
        return plan, {}

    case_block = "\n\n".join(
        f"--- Test Case ---\n{_build_full_case_payload(tc)}" for tc in tc_full_payloads
    )
    user_msg = (
        f"Application URL: {app_url}\n\n"
        f"Test cases to plan ({len(tc_full_payloads)} total):\n\n"
        f"{case_block}\n\n"
        "Return the execution plan JSON now. Remember to populate merged_steps for "
        "shared groups to eliminate duplicate login/navigation steps."
    )

    llm = get_llm_client()

    for attempt in range(1, max_retries + 2):
        try:
            response = await asyncio.to_thread(
                llm.chat_sync,
                messages=[
                    Message(role="system", content=_PLANNER_SYSTEM_PROMPT),
                    Message(role="user", content=user_msg),
                ],
                temperature=0.1,
            )
            text = str(getattr(response, "content", "") or "")
            data = _extract_json(text)
            if data and data.get("groups"):
                plan = _parse_plan(data, app_url)
                origin_map = plan.build_step_origin_map()
                logger.info(
                    f"[PlannerAgent] Plan: {len(plan.groups)} groups, "
                    f"{plan.parallelism} lanes, {plan.total_cases} cases, "
                    f"{len(origin_map)} merged-step origins"
                )
                return plan, origin_map
            logger.warning(
                f"[PlannerAgent] Attempt {attempt}: could not parse JSON from LLM output."
            )
        except Exception as exc:
            logger.warning(f"[PlannerAgent] Attempt {attempt} error: {exc}")

    logger.warning("[PlannerAgent] All attempts failed — using sequential fallback plan.")
    fallback = _fallback_sequential_plan(tc_full_payloads, app_url)
    return fallback, {}
