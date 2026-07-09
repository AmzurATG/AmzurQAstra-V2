"""
Evaluator Agent — fans merged group execution results back to individual test cases.

After SharedSessionRunner executes a group's merged script, this module:
  1. Receives merged_step_results (one entry per merged step, with screenshot_path).
  2. Uses StepOriginMap to find which original (tc_id, step_number) each merged step satisfies.
  3. Builds per-TC step_results lists with status, actual_result, adaptation, screenshot_path.
  4. Slices agent_logs to only the segments that satisfy that TC (no group-wide log dump).
  5. Determines per-TC overall verdict (passed / failed / error).
  6. Never invents a primary screenshot from an unrelated group frame.

This is pure Python — no I/O, no browser, easy to unit test.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from common.utils.logger import logger
from features.functional.core.execution.execution_plan import ExecutionGroup, StepOriginMap


def _distinct_screenshot_paths(step_results: List[Dict[str, Any]]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for s in step_results:
        p = s.get("screenshot_path")
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _slice_agent_logs_for_case(
    agent_logs: List[Dict[str, Any]],
    merged_step_results: List[Dict[str, Any]],
    relevant_merged_nums: Set[int],
) -> List[Dict[str, Any]]:
    """Keep only log entries belonging to merged steps that satisfy this case."""
    if not agent_logs:
        return []
    if not relevant_merged_nums:
        return []

    # Prefer explicit log index ranges stamped by the segmented runner.
    ranges: List[Tuple[int, int]] = []
    for ms in merged_step_results:
        num = ms.get("merged_step_number")
        if num not in relevant_merged_nums:
            continue
        start = ms.get("log_start_index")
        end = ms.get("log_end_index")
        if isinstance(start, int) and isinstance(end, int) and end > start:
            ranges.append((start, end))

    if ranges:
        ranges.sort()
        out: List[Dict[str, Any]] = []
        seen_idx: Set[int] = set()
        for start, end in ranges:
            for i in range(max(0, start), min(len(agent_logs), end)):
                if i in seen_idx:
                    continue
                seen_idx.add(i)
                out.append(agent_logs[i])
        return out

    # Fallback: keep headers whose ▶ Step N matches, plus following action lines
    # until the next header. Also keep entries whose screenshot matches a relevant step.
    relevant_shots = {
        ms.get("screenshot_path")
        for ms in merged_step_results
        if ms.get("merged_step_number") in relevant_merged_nums and ms.get("screenshot_path")
    }
    out = []
    keep = False
    for entry in agent_logs:
        desc = (entry.get("description") or "").strip()
        if desc.startswith("▶"):
            keep = False
            for num in relevant_merged_nums:
                if f"Step {num}/" in desc or f"Step {num} " in desc:
                    keep = True
                    break
            if keep:
                out.append(entry)
            continue
        if keep:
            out.append(entry)
        elif entry.get("screenshot_path") in relevant_shots:
            out.append(entry)
    return out


def evaluate_group_results(
    *,
    group: ExecutionGroup,
    group_result: Dict[str, Any],
    step_origin_map: StepOriginMap,
    tc_data: Dict[int, Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """
    Fan merged group execution results back to per-TC per-step rows.

    Returns
    -------
    Dict[int, Dict[str, Any]] — keyed by tc_id, values have:
        step_results, overall, summary, screenshots, screenshot_path,
        duration_ms, group_duration_ms, shared_session, agent_logs,
        agent_screenshot_count, error
    """
    overall_group = group_result.get("overall", "error")
    merged_step_results: List[Dict[str, Any]] = group_result.get("merged_step_results", [])
    group_summary = group_result.get("summary", "")
    group_duration = int(group_result.get("duration_ms", 0) or 0)
    group_error = group_result.get("error")
    agent_logs: List[Dict[str, Any]] = list(group_result.get("agent_logs") or [])

    n_cases = max(1, len(group.ordered_cases))
    # Shared groups: attribute an equal share of wall time so every case does not
    # show the full group duration (misleading "372s" on every sibling).
    per_case_duration = (
        group_duration // n_cases if group.is_shared and n_cases > 1 else group_duration
    )

    merged_by_num: Dict[int, Dict[str, Any]] = {
        r["merged_step_number"]: r for r in merged_step_results if r.get("merged_step_number")
    }

    # (tc_id, original_step_number) → merged_step_result
    origin_lookup: Dict[tuple, Dict[str, Any]] = {}
    # tc_id → set of merged_step_numbers that satisfy it
    tc_merged_nums: Dict[int, Set[int]] = {p.tc_id: set() for p in group.ordered_cases}

    for g in [group]:
        for ms in g.merged_steps:
            key_str = f"{g.group_id}:{ms.merged_step_number}"
            ms_result = merged_by_num.get(ms.merged_step_number)
            if ms_result is None:
                continue
            for orig in step_origin_map.get(key_str, []):
                tc_id = orig.get("tc_id")
                step_num = orig.get("step_number")
                if tc_id and step_num:
                    origin_lookup[(tc_id, step_num)] = ms_result
                    tc_merged_nums.setdefault(tc_id, set()).add(ms.merged_step_number)

    results_by_tc: Dict[int, Dict[str, Any]] = {}

    for planned in group.ordered_cases:
        tc_id = planned.tc_id
        tc = tc_data.get(tc_id, {})
        original_steps: List[Dict[str, Any]] = tc.get("steps", [])

        step_results: List[Dict[str, Any]] = []
        relevant_merged: Set[int] = set()

        if group.is_shared and group.merged_steps:
            for s_orig in sorted(original_steps, key=lambda x: x.get("step_number", 0)):
                step_num = s_orig.get("step_number", 0)
                ms_result = origin_lookup.get((tc_id, step_num))

                if ms_result:
                    status = ms_result.get("status", "skipped")
                    actual_result = ms_result.get("actual_result", "")
                    adaptation = ms_result.get("adaptation")
                    screenshot_path = ms_result.get("screenshot_path")
                    agent_actions = ms_result.get("agent_actions") or []
                    verdict_source = ms_result.get("verdict_source")
                    mnum = ms_result.get("merged_step_number")
                    if mnum is not None:
                        relevant_merged.add(int(mnum))
                else:
                    status = "skipped"
                    actual_result = "Step not covered by the merged execution script."
                    adaptation = None
                    screenshot_path = None
                    agent_actions = []
                    verdict_source = None

                step_results.append({
                    **s_orig,
                    "step_number": step_num,
                    "status": status,
                    "actual_result": actual_result,
                    "adaptation": adaptation,
                    "screenshot_path": screenshot_path,
                    "agent_actions": agent_actions,
                    "verdict_source": verdict_source,
                })
        else:
            raw_step_results = group_result.get("step_results", [])
            sr_by_num = {r.get("step_number"): r for r in (raw_step_results or [])}
            for s_orig in sorted(original_steps, key=lambda x: x.get("step_number", 0)):
                step_num = s_orig.get("step_number", 0)
                s_res = sr_by_num.get(step_num, {})
                step_results.append({
                    **s_orig,
                    "step_number": step_num,
                    "status": s_res.get("status", "skipped"),
                    "actual_result": s_res.get("actual_result"),
                    "adaptation": s_res.get("adaptation"),
                    "screenshot_path": s_res.get("screenshot_path"),
                    "agent_actions": s_res.get("agent_actions") or [],
                    "verdict_source": s_res.get("verdict_source"),
                })
            # Isolated synthetic groups: all merged steps belong to this one case.
            relevant_merged = {
                int(r["merged_step_number"])
                for r in merged_step_results
                if r.get("merged_step_number") is not None
            }

        if not relevant_merged:
            relevant_merged = tc_merged_nums.get(tc_id, set())

        tc_screenshots = _distinct_screenshot_paths(step_results)

        any_failed = any(s.get("status") not in ("passed",) for s in step_results)
        if overall_group == "cancelled":
            tc_overall = "cancelled"
        elif overall_group == "error":
            tc_overall = "error"
        elif any_failed:
            tc_overall = "failed"
        else:
            tc_overall = "passed"

        # Primary screenshot: ONLY from this case's own step evidence.
        # Never fall back to an unrelated group frame (that caused "same shot for everyone").
        primary_screenshot: Optional[str] = None
        for s in step_results:
            if s.get("status") not in ("passed",) and s.get("screenshot_path"):
                primary_screenshot = s["screenshot_path"]
                break
        if not primary_screenshot and tc_screenshots:
            primary_screenshot = tc_screenshots[-1]

        case_logs = _slice_agent_logs_for_case(
            agent_logs, merged_step_results, relevant_merged
        )
        # Badge / UI count = number of steps with a screenshot (matches expanded strip),
        # not distinct files (shared merge can reuse one PNG across steps).
        shot_count = sum(1 for s in step_results if s.get("screenshot_path"))
        if shot_count == 0 and case_logs:
            shot_count = len({
                e.get("screenshot_path")
                for e in case_logs
                if isinstance(e, dict) and e.get("screenshot_path")
            })

        results_by_tc[tc_id] = {
            "overall": tc_overall,
            "step_results": step_results,
            "screenshots": tc_screenshots,
            "screenshot_path": primary_screenshot,
            "summary": group_summary,
            "duration_ms": per_case_duration,
            "group_duration_ms": group_duration,
            "shared_session": bool(group.is_shared and n_cases > 1),
            "agent_logs": case_logs,
            "agent_screenshot_count": shot_count,
            "error": group_error if tc_overall in ("error",) else None,
        }

        logger.info(
            f"[EvaluatorAgent] tc_id={tc_id} overall={tc_overall} "
            f"steps={len(step_results)} screenshots={shot_count} "
            f"logs={len(case_logs)} shared={group.is_shared}"
        )

    return results_by_tc
