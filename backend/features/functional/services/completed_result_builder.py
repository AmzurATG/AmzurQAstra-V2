"""
Build CompletedCaseResult-shaped dicts for live progress and DB fallback.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from features.functional.db.models.test_result import TestResult

LITE_STRIP_KEYS = ("step_results", "adapted_steps", "original_steps", "agent_logs")


def _count_step_screenshots(step_results: Optional[List[Dict[str, Any]]]) -> int:
    """Count steps that have a screenshot (matches UI strip), not distinct files."""
    if not step_results:
        return 0
    return sum(
        1 for s in step_results if isinstance(s, dict) and s.get("screenshot_path")
    )


def _count_agent_screenshots(agent_logs: Optional[List[Dict[str, Any]]]) -> int:
    if not agent_logs:
        return 0
    return sum(
        1 for e in agent_logs if isinstance(e, dict) and e.get("screenshot_path")
    )


def completed_case_to_lite(d: Dict[str, Any]) -> Dict[str, Any]:
    """Shrink one completed-case dict for fast /live polling (no heavy JSON blobs)."""
    n = d.get("agent_screenshot_count")
    if n is None:
        n = _count_step_screenshots(d.get("step_results"))
    if not n:
        n = _count_agent_screenshots(d.get("agent_logs"))
    if not n and d.get("screenshot_path"):
        n = 1
    has_adapt = bool(d.get("adapted_steps")) or bool(d.get("has_adaptations"))
    inferred = d.get("has_inferred_verdicts")
    if inferred is None and d.get("step_results"):
        inferred = any(
            isinstance(s, dict)
            and str(s.get("verdict_source") or "").startswith("inferred")
            for s in (d.get("step_results") or [])
        )
    out = {k: v for k, v in d.items() if k not in LITE_STRIP_KEYS}
    for k in LITE_STRIP_KEYS:
        out[k] = None
    out["agent_screenshot_count"] = int(n) if n is not None else 0
    out["has_adaptations"] = has_adapt
    out["has_inferred_verdicts"] = bool(inferred)
    return out


def live_progress_to_lite(body: Dict[str, Any], *, log_cap: int = 200) -> Dict[str, Any]:
    """Trim completed_results and logs for low-latency polling."""
    cr = body.get("completed_results") or []
    lite_results = [
        completed_case_to_lite(x) if isinstance(x, dict) else x for x in cr
    ]
    logs = body.get("logs") or []
    if log_cap > 0 and len(logs) > log_cap:
        logs = logs[-log_cap:]
    return {**body, "completed_results": lite_results, "logs": logs}


def completed_case_dict(
    *,
    test_result_id: int,
    test_case_id: int,
    title: str,
    status: str,
    steps_total: int,
    steps_passed: int,
    steps_failed: int,
    duration_ms: int,
    step_results: Optional[List[Dict[str, Any]]] = None,
    adapted_steps: Optional[List[Dict[str, Any]]] = None,
    original_steps: Optional[List[Dict[str, Any]]] = None,
    agent_logs: Optional[List[Dict[str, Any]]] = None,
    screenshot_path: Optional[str] = None,
    failed_step: Optional[int] = None,
    failure_reason: Optional[str] = None,
    has_inferred_verdicts: Optional[bool] = None,
    agent_screenshot_count: Optional[int] = None,
    shared_session: Optional[bool] = None,
    group_duration_ms: Optional[int] = None,
) -> Dict[str, Any]:
    inferred = has_inferred_verdicts
    if inferred is None and step_results:
        inferred = any(
            isinstance(s, dict)
            and str(s.get("verdict_source") or "").startswith("inferred")
            for s in step_results
        )
    reason = failure_reason
    if reason is None and status != "passed" and step_results:
        for s in step_results:
            if isinstance(s, dict) and s.get("status") not in ("passed", None):
                reason = (s.get("actual_result") or "")[:240] or None
                if failed_step is None:
                    failed_step = s.get("step_number")
                break
    shot_count = agent_screenshot_count
    if shot_count is None:
        shot_count = _count_step_screenshots(step_results)
    if not shot_count:
        shot_count = _count_agent_screenshots(agent_logs)
    if not shot_count and screenshot_path:
        shot_count = 1
    return {
        "test_result_id": test_result_id,
        "test_case_id": test_case_id,
        "title": title,
        "status": status,
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "duration_ms": duration_ms,
        "step_results": step_results,
        "adapted_steps": adapted_steps,
        "original_steps": original_steps,
        "agent_logs": agent_logs,
        "screenshot_path": screenshot_path,
        "agent_screenshot_count": int(shot_count or 0),
        "failed_step": failed_step,
        "failure_reason": reason,
        "has_inferred_verdicts": bool(inferred),
        "shared_session": bool(shared_session) if shared_session is not None else None,
        "group_duration_ms": group_duration_ms,
    }


def completed_case_dict_from_orm(tr: TestResult) -> Dict[str, Any]:
    """Requires test_case relationship loaded for best title."""
    tc = getattr(tr, "test_case", None)
    title = (tc.title or f"Test Case #{tr.test_case_id}") if tc else f"Test Case #{tr.test_case_id}"
    sr = tr.step_results or []
    steps_passed = sum(1 for s in sr if s.get("status") == "passed")
    steps_failed = sum(1 for s in sr if s.get("status") != "passed")
    st = tr.status.value if hasattr(tr.status, "value") else str(tr.status)
    return completed_case_dict(
        test_result_id=tr.id,
        test_case_id=tr.test_case_id,
        title=title,
        status=st,
        steps_total=len(sr),
        steps_passed=steps_passed,
        steps_failed=steps_failed,
        duration_ms=tr.duration_ms or 0,
        step_results=tr.step_results,
        adapted_steps=tr.adapted_steps,
        original_steps=tr.original_steps,
        agent_logs=tr.agent_logs,
        screenshot_path=tr.screenshot_path,
        failed_step=tr.failed_step,
        agent_screenshot_count=_count_step_screenshots(sr) or _count_agent_screenshots(tr.agent_logs),
    )
