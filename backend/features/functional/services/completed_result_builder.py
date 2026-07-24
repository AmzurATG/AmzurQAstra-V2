"""
Build CompletedCaseResult-shaped dicts for live progress and DB fallback.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from features.functional.core.grouping.setup_step_merger import compute_step_display_counts
from features.functional.db.models.test_result import TestResult
from features.functional.core.case_budget import format_duration_ms

LITE_STRIP_KEYS = ("step_results", "adapted_steps", "original_steps", "agent_logs")


def _count_agent_screenshots(agent_logs: Optional[List[Dict[str, Any]]]) -> int:
    if not agent_logs:
        return 0
    evidence = [
        e
        for e in agent_logs
        if isinstance(e, dict) and e.get("screenshot_path") and e.get("evidence", True) is not False
    ]
    # Prefer curated evidence tags when present
    if any(isinstance(e, dict) and e.get("evidence") is True for e in agent_logs):
        return sum(1 for e in agent_logs if isinstance(e, dict) and e.get("evidence") is True and e.get("screenshot_path"))
    return sum(1 for e in evidence if e.get("screenshot_path"))


def completed_case_to_lite(d: Dict[str, Any]) -> Dict[str, Any]:
    """Shrink one completed-case dict for fast /live polling (no heavy JSON blobs)."""
    n = d.get("agent_screenshot_count")
    if n is None:
        ai = d.get("ai_modified") or {}
        n = ai.get("evidence_screenshot_count")
    if n is None:
        n = _count_agent_screenshots(d.get("agent_logs"))
    has_adapt = bool(d.get("adapted_steps"))
    out = {k: v for k, v in d.items() if k not in LITE_STRIP_KEYS}
    for k in LITE_STRIP_KEYS:
        out[k] = None
    out["agent_screenshot_count"] = int(n) if n is not None else 0
    out["has_adaptations"] = has_adapt
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
    shots = body.get("live_screenshots") or []
    if len(shots) > 12:
        shots = shots[-12:]
    return {
        **body,
        "completed_results": lite_results,
        "logs": logs,
        # Keep lanes/groups out of the user-facing live payload — sequential UX only.
        "active_lanes": [],
        "groups": [],
        "live_screenshots": list(shots),
        "ui_desync": False,
        "ui_desync_events": [],
        "watchdog": None,
        "supervisor": None,
        "health": None,
        "health_summary": None,
        "runtime_banner": body.get("runtime_banner"),
        "llm_health": None,
    }


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
    ai_modified: Optional[Dict[str, Any]] = None,
    ui_override: bool = False,
    ui_validation: Optional[Dict[str, Any]] = None,
    executor_status: Optional[str] = None,
    verdict_source: Optional[str] = None,
    setup_skipped_count: int = 0,
    jira_bug_key: Optional[str] = None,
    jira_bug_url: Optional[str] = None,
) -> Dict[str, Any]:
    # Prefer verified counts derived from step_results when present.
    if step_results is not None:
        counts = compute_step_display_counts(step_results)
        steps_total = counts["steps_total"]
        steps_passed = counts["steps_passed"]
        steps_failed = counts["steps_failed"]
        setup_skipped_count = counts["setup_skipped_count"]
    ai = ai_modified or {}
    evidence_n = ai.get("evidence_screenshot_count")
    shot_count = (
        int(evidence_n)
        if evidence_n is not None
        else _count_agent_screenshots(agent_logs)
    )
    return {
        "test_result_id": test_result_id,
        "test_case_id": test_case_id,
        "title": title,
        "status": status,
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "setup_skipped_count": setup_skipped_count,
        "duration_ms": duration_ms,
        "duration_display": format_duration_ms(duration_ms),
        "step_results": step_results,
        "adapted_steps": adapted_steps,
        "original_steps": original_steps,
        "agent_logs": agent_logs,
        "screenshot_path": screenshot_path,
        "agent_screenshot_count": shot_count,
        "ai_modified": ai_modified,
        "has_adaptations": bool(adapted_steps) or bool(
            ai_modified and ai_modified.get("has_changes")
        ),
        "ui_override": bool(ui_override) or bool(
            ai_modified and ai_modified.get("ui_override")
        ),
        "ui_validation": ui_validation
        or ((ai_modified or {}).get("ui_validation") if ai_modified else None),
        "executor_status": executor_status
        or ((ai_modified or {}).get("executor_status") if ai_modified else None),
        "verdict_source": verdict_source
        or ((ai_modified or {}).get("verdict_source") if ai_modified else None),
        "user_message": ai.get("user_message"),
        "infra_error": bool(ai.get("infra_error")),
        "error_kind": ai.get("error_kind"),
        "jira_bug_key": jira_bug_key,
        "jira_bug_url": jira_bug_url,
    }


def completed_case_dict_from_orm(tr: TestResult) -> Dict[str, Any]:
    """Requires test_case relationship loaded for best title."""
    tc = getattr(tr, "test_case", None)
    title = (tc.title or f"Test Case #{tr.test_case_id}") if tc else f"Test Case #{tr.test_case_id}"
    sr = tr.step_results or []
    counts = compute_step_display_counts(sr)
    st = tr.status.value if hasattr(tr.status, "value") else str(tr.status)
    return completed_case_dict(
        test_result_id=tr.id,
        test_case_id=tr.test_case_id,
        title=title,
        status=st,
        steps_total=counts["steps_total"],
        steps_passed=counts["steps_passed"],
        steps_failed=counts["steps_failed"],
        setup_skipped_count=counts["setup_skipped_count"],
        duration_ms=tr.duration_ms or 0,
        step_results=tr.step_results,
        adapted_steps=tr.adapted_steps,
        original_steps=tr.original_steps,
        agent_logs=tr.agent_logs,
        screenshot_path=tr.screenshot_path,
        ai_modified=getattr(tr, "ai_modified", None),
        jira_bug_key=getattr(tr, "jira_bug_key", None),
        jira_bug_url=getattr(tr, "jira_bug_url", None),
    )
