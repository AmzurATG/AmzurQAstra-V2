"""
Evaluator Agent — fans merged group execution results back to individual test cases.

After SharedSessionRunner executes a group's merged script, this module:
  1. Receives merged_step_results (one entry per merged step, with screenshot_path).
  2. Uses StepOriginMap to find which original (tc_id, step_number) each merged step satisfies.
  3. Builds per-TC step_results lists with status, actual_result, adaptation, screenshot_path.
  4. Determines per-TC overall verdict (passed / failed / error).
  5. For isolated groups (no merged steps), falls back to direct per-case step attribution.

This is pure Python — no I/O, no browser, easy to unit test.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from common.utils.logger import logger
from features.functional.core.execution.execution_plan import ExecutionGroup, StepOriginMap


def evaluate_group_results(
    *,
    group: ExecutionGroup,
    group_result: Dict[str, Any],
    step_origin_map: StepOriginMap,
    tc_data: Dict[int, Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """
    Fan merged group execution results back to per-TC per-step rows.

    Parameters
    ----------
    group:
        The ExecutionGroup that was just executed.
    group_result:
        Dict returned by SharedSessionRunner.run_group().
        Keys: overall, merged_step_results, agent_logs, screenshots, summary, duration_ms, error.
    step_origin_map:
        Map of "{group_id}:{merged_step_number}" → [{tc_id, step_number}].
        Built from GroupedRunPlan.build_step_origin_map().
    tc_data:
        {tc_id: {"title", "steps": [...]}} — full step definitions per case.

    Returns
    -------
    Dict[int, Dict[str, Any]] — keyed by tc_id, values have:
        step_results, overall, summary, screenshots, duration_ms, error
    """
    overall_group = group_result.get("overall", "error")
    merged_step_results: List[Dict[str, Any]] = group_result.get("merged_step_results", [])
    group_summary = group_result.get("summary", "")
    group_duration = group_result.get("duration_ms", 0)
    group_error = group_result.get("error")
    group_screenshots = group_result.get("screenshots", [])

    # Build lookup: merged_step_number → merged_step_result (with screenshot)
    merged_by_num: Dict[int, Dict[str, Any]] = {
        r["merged_step_number"]: r for r in merged_step_results if r.get("merged_step_number")
    }

    # Build lookup: (tc_id, original_step_number) → merged_step_result
    # One original step may be satisfied by one merged step
    origin_lookup: Dict[tuple, Dict[str, Any]] = {}
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

    results_by_tc: Dict[int, Dict[str, Any]] = {}

    for planned in group.ordered_cases:
        tc_id = planned.tc_id
        tc = tc_data.get(tc_id, {})
        original_steps: List[Dict[str, Any]] = tc.get("steps", [])

        step_results: List[Dict[str, Any]] = []
        tc_screenshots: List[str] = []

        if group.is_shared and group.merged_steps:
            # Fan-out: map each original step to a merged step result
            for s_orig in sorted(original_steps, key=lambda x: x.get("step_number", 0)):
                step_num = s_orig.get("step_number", 0)
                ms_result = origin_lookup.get((tc_id, step_num))

                if ms_result:
                    status = ms_result.get("status", "skipped")
                    actual_result = ms_result.get("actual_result", "")
                    adaptation = ms_result.get("adaptation")
                    screenshot_path = ms_result.get("screenshot_path")
                else:
                    # Original step not covered by any merged step — mark as skipped
                    status = "skipped"
                    actual_result = "Step not covered by the merged execution script."
                    adaptation = None
                    screenshot_path = None

                if screenshot_path and screenshot_path not in tc_screenshots:
                    tc_screenshots.append(screenshot_path)

                step_results.append({
                    **s_orig,
                    "step_number": step_num,
                    "status": status,
                    "actual_result": actual_result,
                    "adaptation": adaptation,
                    "screenshot_path": screenshot_path,
                })
        else:
            # Isolated group: the group_result overall applies to the single case
            # Step detail comes from the legacy step_results if available
            raw_step_results = group_result.get("step_results", [])
            sr_by_num = {r.get("step_number"): r for r in (raw_step_results or [])}
            for s_orig in sorted(original_steps, key=lambda x: x.get("step_number", 0)):
                step_num = s_orig.get("step_number", 0)
                s_res = sr_by_num.get(step_num, {})
                screenshot_path = s_res.get("screenshot_path")
                if screenshot_path and screenshot_path not in tc_screenshots:
                    tc_screenshots.append(screenshot_path)
                step_results.append({
                    **s_orig,
                    "step_number": step_num,
                    "status": s_res.get("status", "skipped"),
                    "actual_result": s_res.get("actual_result"),
                    "adaptation": s_res.get("adaptation"),
                    "screenshot_path": screenshot_path,
                })

        # Determine per-TC overall from its step results
        any_failed = any(s.get("status") not in ("passed",) for s in step_results)
        if overall_group == "cancelled":
            tc_overall = "cancelled"
        elif overall_group == "error":
            tc_overall = "error"
        elif any_failed:
            tc_overall = "failed"
        else:
            tc_overall = "passed"

        # Best screenshot: first failed step's, or last step's
        primary_screenshot: Optional[str] = None
        for s in step_results:
            if s.get("status") not in ("passed",) and s.get("screenshot_path"):
                primary_screenshot = s["screenshot_path"]
                break
        if not primary_screenshot and tc_screenshots:
            primary_screenshot = tc_screenshots[-1]
        if not primary_screenshot and group_screenshots:
            primary_screenshot = group_screenshots[-1]

        results_by_tc[tc_id] = {
            "overall": tc_overall,
            "step_results": step_results,
            "screenshots": tc_screenshots,
            "screenshot_path": primary_screenshot,
            "summary": group_summary,
            "duration_ms": group_duration,
            "error": group_error if tc_overall in ("error",) else None,
        }

        logger.info(
            f"[EvaluatorAgent] tc_id={tc_id} overall={tc_overall} "
            f"steps={len(step_results)} screenshots={len(tc_screenshots)}"
        )

    return results_by_tc
