"""
Build CompletedCaseResult-shaped dicts for live progress and DB fallback.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from features.functional.db.models.test_result import TestResult


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
) -> Dict[str, Any]:
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
    )
