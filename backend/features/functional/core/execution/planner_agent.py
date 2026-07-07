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

from config import settings
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

# Max parallel browser lanes the planner may assign. Single source of truth =
# the Steel concurrency budget (free=5, dev=20, pro=100). Set via .env.
MAX_LANES = max(1, settings.MAX_CONCURRENT_BROWSERS)

_PLANNER_SYSTEM_PROMPT = """\
You are an expert QA test orchestration planner with deep understanding of web application flows.

Your job: given a list of test cases with full step definitions, create an intelligent execution plan that:
1. Groups cases that can share a browser session (login once, run multiple).
2. Merges duplicate/equivalent steps across cases in a group into a single merged script.
3. Assigns groups to parallel browser lanes for maximum speed.

## GROUPING RULES

1. **Shared session** (`session_type: "shared"`) — THIS IS THE DEFAULT. Prefer it strongly.
   - ANY cases that require valid authenticated access belong together — login once, run all.
   - This INCLUDES cases that perform DIFFERENT actions or CRUD mutations (create admin, change
     role, deactivate, filter list, view audit log). Different actions and data changes are FINE
     in a shared session — run them sequentially after a single login. Do NOT isolate a case just
     because it creates/edits/deletes data or "verifies" something different.
   - Group by feature area (all admin-account cases together, all league-filter cases together).
   - Aim to put the large majority (60-80%) of authenticated cases into a handful of shared groups.
   - GROUP SIZE LIMIT: put at most {max_cases_per_group} cases in any single shared group. If a
     feature area has more, split it into multiple shared groups (e.g. "Admin – Accounts A",
     "Admin – Accounts B") and place them on different lanes. This keeps each browser run fast.
   - Within a shared group, order cases logically (setup first, then verification, logout last).

2. **Chaining negative + positive flows in ONE shared session** (HIGH VALUE — do this aggressively):
   - A FAILED login attempt (wrong password / invalid email) leaves the browser ON the login
     page. You do NOT need a fresh browser to then attempt a valid login. So CHAIN them:
     first run the negative case (wrong creds → assert error), then continue in the SAME
     session with the valid login, then run any authenticated cases after that.
   - Example: "Login with invalid credentials" + "Login with valid credentials" + "View dashboard"
     → ONE shared group: attempt wrong creds (satisfies the negative case), assert the error,
     clear the fields, enter correct creds (satisfies the valid-login case + logs in), then the
     authenticated cases run on top. Two-to-many test cases, one browser, no relogin.
   - Generalize this: any sequence of negative-then-recover flows (wrong→right, empty→filled,
     invalid format→valid) belongs in ONE shared session. Aim to combine 40-60% of cases this way.

3. **Isolated session** (`session_type: "isolated"`) — use ONLY when clean state is truly required:
   - Cases that MUTATE auth state for everyone after them: account-lockout after N attempts,
     "account locked/disabled", rate-limit/captcha-trigger tests.
   - Cases whose preconditions explicitly demand it: "clear cookies", "fresh/incognito session",
     "must start logged out", session-timeout / token-expiry / remember-me persistence tests.
   - When in doubt and the case does NOT corrupt shared state, prefer SHARED + chaining (rule 2).

4. **Step Merging** (CRITICAL — this is the core value):
   - Within a shared group, find steps with the same ACTION and INTENT across cases.
   - Common duplicates: "Navigate to app URL", "Login with valid credentials", "Open dashboard".
   - Create ONE merged step that runs once and satisfies the equivalent step in every case.
   - Each merged step has a `satisfies` list: [{tc_id, step_number}] for every original step it covers.
   - Case-specific steps that only apply to one case get their own merged step with satisfies=[{that case only}].
   - The merged script runs top-to-bottom in one browser: shared prefix steps first, then case-specific segments.
   - COMPLETENESS (mandatory): EVERY original step of EVERY case in the group MUST appear in exactly one
     merged step's `satisfies` list. Never drop a step. Uncovered original steps show up blank/"skipped"
     in the per-case report, so account for all of them.

5. **Browser lanes** (parallel execution):
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
""".replace("{max_lanes}", str(MAX_LANES)).replace(
    "{max_cases_per_group}", str(max(1, settings.MAX_CASES_PER_SHARED_GROUP))
)


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


def _looks_like_login(step: Dict[str, Any]) -> bool:
    txt = f"{step.get('action','')} {step.get('description','')} {step.get('target','')}".lower()
    return any(k in txt for k in ("login", "log in", "sign in", "signin", "authenticate"))


def _looks_like_nav(step: Dict[str, Any]) -> bool:
    txt = f"{step.get('action','')} {step.get('description','')} {step.get('target','')}".lower()
    return step.get("action") == "navigate" or "navigate" in txt or "open the app" in txt or "go to" in txt


def _is_negative_auth(tc: Dict[str, Any]) -> bool:
    st = (tc.get("scenario_type") or "").lower()
    title = (tc.get("title") or "").lower()
    return st == "negative" and any(
        k in title for k in ("login", "password", "auth", "2fa", "otp", "lock", "credential", "sign in")
    )


def _needs_clean_state(tc: Dict[str, Any]) -> bool:
    blob = f"{tc.get('title','')} {tc.get('preconditions','')}".lower()
    return any(k in blob for k in (
        "clear cookie", "fresh session", "incognito", "logged out", "log out",
        "lockout", "locked", "rate limit", "session timeout", "token expiry", "remember me",
    ))


def _deterministic_grouped_plan(
    tc_full_payloads: List[Dict[str, Any]], app_url: str
) -> GroupedRunPlan:
    """
    LLM-free fallback that STILL merges: positive authenticated cases are chunked into
    shared groups (login once, run each case's steps in the same browser); negative-auth
    and clean-state cases stay isolated for safety. Guarantees every original step is
    covered by exactly one merged step (so per-case step display stays complete).
    """
    isolated: List[Dict[str, Any]] = []
    shareable: List[Dict[str, Any]] = []
    for tc in tc_full_payloads:
        if not tc.get("steps"):
            isolated.append(tc)
        elif _is_negative_auth(tc) or _needs_clean_state(tc):
            isolated.append(tc)
        else:
            shareable.append(tc)

    groups: List[ExecutionGroup] = []
    gid = 1
    cap = max(1, int(settings.MAX_CASES_PER_SHARED_GROUP))

    for i in range(0, len(shareable), cap):
        chunk = shareable[i : i + cap]
        merged: List[MergedStep] = []
        msn = 1
        used: Dict[int, set] = {tc["tc_id"]: set() for tc in chunk}

        # Shared login/nav prefix taken from the FIRST (positive) case, satisfying the
        # equivalent login/nav step in every case in the chunk → login happens once.
        prefix = [
            s for s in sorted(chunk[0]["steps"], key=lambda x: x.get("step_number", 0))
            if _looks_like_login(s) or _looks_like_nav(s)
        ]
        for ps in prefix:
            satisfies: List[Dict[str, int]] = []
            for tc in chunk:
                for s in sorted(tc["steps"], key=lambda x: x.get("step_number", 0)):
                    if s.get("step_number") in used[tc["tc_id"]]:
                        continue
                    same = (_looks_like_login(ps) and _looks_like_login(s)) or (
                        _looks_like_nav(ps) and _looks_like_nav(s)
                    )
                    if same:
                        satisfies.append({"tc_id": tc["tc_id"], "step_number": s["step_number"]})
                        used[tc["tc_id"]].add(s["step_number"])
                        break
            merged.append(MergedStep(
                merged_step_number=msn, action=ps.get("action", "custom"),
                description=ps.get("description", ""), target=ps.get("target") or None,
                value=ps.get("value") or None, expected_result=ps.get("expected_result") or None,
                satisfies=satisfies,
            ))
            msn += 1

        # Every remaining step of every case → its own merged step (completeness).
        for tc in chunk:
            for s in sorted(tc["steps"], key=lambda x: x.get("step_number", 0)):
                if s.get("step_number") in used[tc["tc_id"]]:
                    continue
                merged.append(MergedStep(
                    merged_step_number=msn, action=s.get("action", "custom"),
                    description=s.get("description", ""), target=s.get("target") or None,
                    value=s.get("value") or None, expected_result=s.get("expected_result") or None,
                    satisfies=[{"tc_id": tc["tc_id"], "step_number": s["step_number"]}],
                ))
                msn += 1

        groups.append(ExecutionGroup(
            group_id=f"G{gid}", label=f"Auto-merged group {gid}", session_type="shared",
            browser_lane=((gid - 1) % MAX_LANES) + 1, reset_url=app_url,
            ordered_cases=[
                PlannedCase(tc_id=tc["tc_id"], order=j + 1, reset_before=None,
                            reason="deterministic login-once fallback")
                for j, tc in enumerate(chunk)
            ],
            merged_steps=merged,
        ))
        gid += 1

    for tc in isolated:
        groups.append(ExecutionGroup(
            group_id=f"G{gid}", label=(tc.get("title") or f"Case {tc['tc_id']}")[:50],
            session_type="isolated", browser_lane=((gid - 1) % MAX_LANES) + 1, reset_url=app_url,
            ordered_cases=[PlannedCase(tc_id=tc["tc_id"], order=1, reset_before=None,
                                       reason="negative/clean-state — isolated")],
            merged_steps=[],
        ))
        gid += 1

    total = sum(len(g.ordered_cases) for g in groups)
    return GroupedRunPlan(
        strategy="grouped_parallel", groups=groups, total_cases=total,
        parallelism=min(MAX_LANES, max(len(groups), 1)),
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


def _per_case_isolated_plan(
    tc_full_payloads: List[Dict[str, Any]], app_url: str
) -> GroupedRunPlan:
    """Small-run plan: no grouping, all cases on ONE lane (run sequentially, simple)."""
    groups: List[ExecutionGroup] = []
    for i, tc in enumerate(tc_full_payloads):
        groups.append(ExecutionGroup(
            group_id=f"G{i+1}", label=(tc.get("title") or f"Case {tc['tc_id']}")[:50],
            session_type="isolated", browser_lane=1, reset_url=app_url,
            ordered_cases=[PlannedCase(tc_id=tc["tc_id"], order=1, reset_before=None,
                                       reason="small run — no grouping, single lane")],
            merged_steps=[],
        ))
    return GroupedRunPlan(
        strategy="grouped_parallel", groups=groups, total_cases=len(tc_full_payloads),
        parallelism=1,
    )


def _rebalance_lanes(groups: List[ExecutionGroup]) -> None:
    """Re-id groups G1..Gn and assign each to the currently least-loaded lane."""
    for idx, g in enumerate(groups, start=1):
        g.group_id = f"G{idx}"
    lane_load: Dict[int, int] = {lane: 0 for lane in range(1, MAX_LANES + 1)}
    for g in sorted(groups, key=lambda x: len(x.ordered_cases), reverse=True):
        lane = min(lane_load, key=lane_load.get)
        g.browser_lane = lane
        lane_load[lane] += max(1, len(g.ordered_cases))


def _enforce_group_size_cap(plan: GroupedRunPlan) -> GroupedRunPlan:
    """
    Deterministically split any SHARED group larger than MAX_CASES_PER_SHARED_GROUP
    into multiple shared groups. The LLM ignores the prompt cap, and oversized groups
    create monster segmented runs that drop screenshots and fail. Each split sub-group
    keeps its own copy of shared steps (login/nav) so it still logs in once.
    """
    cap = max(1, int(settings.MAX_CASES_PER_SHARED_GROUP))
    if all(not g.is_shared or len(g.ordered_cases) <= cap for g in plan.groups):
        return plan  # nothing oversized

    new_groups: List[ExecutionGroup] = []
    for g in plan.groups:
        if not g.is_shared or len(g.ordered_cases) <= cap:
            new_groups.append(g)
            continue
        cases = sorted(g.ordered_cases, key=lambda c: c.order)
        for ci in range(0, len(cases), cap):
            chunk = cases[ci : ci + cap]
            chunk_ids = {c.tc_id for c in chunk}
            sub_merged: List[MergedStep] = []
            msn = 1
            for ms in sorted(g.merged_steps, key=lambda m: m.merged_step_number):
                fsat = [s for s in ms.satisfies if s.get("tc_id") in chunk_ids]
                if not fsat:
                    continue  # this merged step isn't for any case in this chunk
                sub_merged.append(MergedStep(
                    merged_step_number=msn, action=ms.action, description=ms.description,
                    target=ms.target, value=ms.value, expected_result=ms.expected_result,
                    satisfies=fsat,
                ))
                msn += 1
            new_groups.append(ExecutionGroup(
                group_id=g.group_id, label=g.label, session_type="shared",
                browser_lane=g.browser_lane, reset_url=g.reset_url,
                ordered_cases=[
                    PlannedCase(tc_id=c.tc_id, order=j + 1, reset_before=c.reset_before, reason=c.reason)
                    for j, c in enumerate(chunk)
                ],
                merged_steps=sub_merged,
            ))

    _rebalance_lanes(new_groups)
    total = sum(len(g.ordered_cases) for g in new_groups)
    split_ct = len(new_groups) - len(plan.groups)
    logger.info(f"[PlannerAgent] Group-size cap ({cap}) split oversized groups: "
                f"{len(plan.groups)} → {len(new_groups)} groups (+{split_ct}).")
    return GroupedRunPlan(
        strategy=plan.strategy, groups=new_groups, total_cases=total,
        parallelism=min(MAX_LANES, max(len(new_groups), 1)),
    )


def _plan_cache_key(tc_full_payloads: List[Dict[str, Any]], app_url: str) -> str:
    """Stable hash of the exact case set + steps + tuning knobs that affect the plan."""
    import hashlib

    canon = []
    for tc in sorted(tc_full_payloads, key=lambda t: t.get("tc_id", 0)):
        steps = [
            (s.get("step_number"), s.get("action"), s.get("target"),
             s.get("value"), s.get("description"), s.get("expected_result"))
            for s in tc.get("steps", [])
        ]
        canon.append((tc.get("tc_id"), tc.get("title"), tc.get("scenario_type"), tuple(steps)))
    blob = json.dumps(
        {"app_url": app_url, "lanes": MAX_LANES,
         "cap": settings.MAX_CASES_PER_SHARED_GROUP, "cases": canon},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load_cached_plan(key: str) -> Optional[Tuple[GroupedRunPlan, StepOriginMap]]:
    if not settings.PLAN_CACHE_ENABLED:
        return None
    import os

    path = os.path.join(settings.PLAN_CACHE_DIR, f"{key}.json")
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        plan = GroupedRunPlan.from_dict(data)
        if not plan.groups:
            return None
        logger.info(f"[PlannerAgent] Reusing CACHED plan ({len(plan.groups)} groups) — skipping LLM planning.")
        return plan, plan.build_step_origin_map()
    except Exception as exc:
        logger.warning(f"[PlannerAgent] Plan cache read failed ({exc}); will re-plan.")
        return None


def _save_cached_plan(key: str, plan: GroupedRunPlan) -> None:
    if not settings.PLAN_CACHE_ENABLED or not plan.groups:
        return
    import os

    try:
        os.makedirs(settings.PLAN_CACHE_DIR, exist_ok=True)
        path = os.path.join(settings.PLAN_CACHE_DIR, f"{key}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f)
        os.replace(tmp, path)
    except Exception as exc:
        logger.warning(f"[PlannerAgent] Plan cache write failed ({exc}); continuing.")


async def build_execution_plan(
    tc_full_payloads: List[Dict[str, Any]],
    app_url: str,
    max_retries: int = 2,
) -> Tuple[GroupedRunPlan, StepOriginMap]:
    """
    Public entry point. Builds a grouped execution plan, automatically BATCHING
    the planner LLM calls when there are many cases so we never overflow the
    model's input/output token limit (the cause of "first N grouped, rest run
    one-by-one"). Scales to thousands of cases.

    For small runs (<= PLANNER_BATCH_SIZE) this is a single LLM call, identical
    to the original behavior.
    """
    if not tc_full_payloads:
        plan = GroupedRunPlan(strategy="sequential", groups=[], total_cases=0, parallelism=1)
        return plan, {}

    # Small runs: skip the LLM planner entirely — nothing meaningful to merge, and
    # planning costs more than it saves. Each case runs directly, isolated but still
    # parallel across lanes (and still per-step screenshots + detailed agent steps).
    if len(tc_full_payloads) < max(1, int(settings.GROUPING_MIN_CASES)):
        logger.info(
            f"[PlannerAgent] {len(tc_full_payloads)} cases < grouping threshold "
            f"({settings.GROUPING_MIN_CASES}) — skipping planner, running per-case."
        )
        plan = _per_case_isolated_plan(tc_full_payloads, app_url)
        return plan, {}

    # Plan cache: identical case set + steps + tuning → reuse, skip the LLM planner.
    cache_key = _plan_cache_key(tc_full_payloads, app_url)
    cached = _load_cached_plan(cache_key)
    if cached is not None:
        plan, _ = cached
        plan = _enforce_group_size_cap(plan)  # safety: re-cap legacy/cached plans
        return plan, plan.build_step_origin_map()

    batch_size = max(1, int(settings.PLANNER_BATCH_SIZE))
    if len(tc_full_payloads) <= batch_size:
        plan, omap = await _build_execution_plan_single(tc_full_payloads, app_url, max_retries)
        plan = _enforce_group_size_cap(plan)
        omap = plan.build_step_origin_map()
        _save_cached_plan(cache_key, plan)
        return plan, omap

    # ── Batch: chunk cases, plan each chunk concurrently, then merge plans ──
    batches = [
        tc_full_payloads[i : i + batch_size]
        for i in range(0, len(tc_full_payloads), batch_size)
    ]
    logger.info(
        f"[PlannerAgent] Batching {len(tc_full_payloads)} cases into "
        f"{len(batches)} planner call(s) of ≤{batch_size}."
    )

    sem = asyncio.Semaphore(max(1, int(settings.PLANNER_MAX_CONCURRENCY)))

    async def _plan_batch(batch: List[Dict[str, Any]]) -> GroupedRunPlan:
        async with sem:
            plan, _ = await _build_execution_plan_single(batch, app_url, max_retries)
            return plan

    batch_plans = await asyncio.gather(*[_plan_batch(b) for b in batches])

    # Concatenate groups, then globally re-id and re-balance lanes.
    merged_groups: List[ExecutionGroup] = []
    for bp in batch_plans:
        merged_groups.extend(bp.groups)

    # Unique, stable group ids across all batches (origin-map keys depend on these).
    for idx, g in enumerate(merged_groups, start=1):
        g.group_id = f"G{idx}"

    # Least-loaded lane assignment so the heaviest groups spread across lanes.
    lane_load: Dict[int, int] = {lane: 0 for lane in range(1, MAX_LANES + 1)}
    for g in sorted(merged_groups, key=lambda x: len(x.ordered_cases), reverse=True):
        lane = min(lane_load, key=lane_load.get)
        g.browser_lane = lane
        lane_load[lane] += max(1, len(g.ordered_cases))

    total = sum(len(g.ordered_cases) for g in merged_groups)
    plan = GroupedRunPlan(
        strategy="grouped_parallel",
        groups=merged_groups,
        total_cases=total,
        parallelism=min(MAX_LANES, max(len(merged_groups), 1)),
    )
    plan = _enforce_group_size_cap(plan)
    origin_map = plan.build_step_origin_map()
    shared = sum(1 for g in merged_groups if g.is_shared)
    logger.info(
        f"[PlannerAgent] Merged batched plan: {len(merged_groups)} groups "
        f"({shared} shared), {plan.parallelism} lanes, {total} cases, "
        f"{len(origin_map)} merged-step origins."
    )
    _save_cached_plan(cache_key, plan)
    return plan, origin_map


async def _build_execution_plan_single(
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
                timeout=settings.PLANNER_LLM_TIMEOUT,
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

    # LLM planning failed — DON'T collapse to all-isolated (that kills merging). Use the
    # deterministic login-once fallback so shared sessions still happen.
    try:
        logger.warning(
            "[PlannerAgent] LLM planning failed — using DETERMINISTIC login-once fallback "
            "(shared groups without the LLM)."
        )
        fallback = _deterministic_grouped_plan(tc_full_payloads, app_url)
        return fallback, fallback.build_step_origin_map()
    except Exception as exc:
        logger.warning(f"[PlannerAgent] Deterministic fallback failed ({exc}) — sequential isolated.")
        seq = _fallback_sequential_plan(tc_full_payloads, app_url)
        return seq, {}
