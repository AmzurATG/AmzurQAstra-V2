"""Report node: persist results to Postgres and finalize run progress."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select

from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.orchestration.state import CaseResult, OrchestrationState
from features.functional.services.completed_result_builder import completed_case_dict
from features.functional.services.run_progress_manager import RunProgressManager


_STATUS_MAP = {
    "passed": TestResultStatus.PASSED,
    "failed": TestResultStatus.FAILED,
    "error": TestResultStatus.ERROR,
    "cancelled": TestResultStatus.SKIPPED,
    "skipped": TestResultStatus.SKIPPED,
}


async def report_node(state: OrchestrationState, *, db_session_factory) -> Dict[str, Any]:
    """Persist case results. db_session_factory injected at invoke time."""
    run_id = int(state["run_id"])
    progress_mgr = RunProgressManager()
    results: List[CaseResult] = list(state.get("case_results") or [])
    retry_map = {int(r["test_case_id"]): r for r in (state.get("retry_results") or [])}
    for cid, rr in retry_map.items():
        # Replace initial result with retry when present
        results = [r for r in results if int(r.get("test_case_id") or 0) != cid]
        results.append(rr)

    completed_payloads: List[Dict[str, Any]] = []
    passed = failed = skipped = 0

    async with db_session_factory() as db:
        for cr in results:
            tr_id = int(cr.get("test_result_id") or 0)
            status_str = str(cr.get("status") or "error")
            db_status = _STATUS_MAP.get(status_str, TestResultStatus.ERROR)
            row = (
                await db.execute(select(TestResult).where(TestResult.id == tr_id))
            ).scalar_one_or_none()
            if row:
                row.status = db_status
                row.duration_ms = int(cr.get("duration_ms") or 0)
                row.step_results = cr.get("step_results")
                row.adapted_steps = cr.get("adapted_steps")
                row.original_steps = cr.get("original_steps")
                row.agent_logs = cr.get("agent_logs")
                row.screenshot_path = cr.get("screenshot_path")
                row.ai_modified = cr.get("ai_modified")
                row.group_id = cr.get("group_id")
                row.worker_id = cr.get("lane_id")
                row.error_message = cr.get("error")
                row.completed_at = datetime.utcnow()
            if status_str == "passed":
                passed += 1
            elif status_str in ("skipped", "cancelled"):
                skipped += 1
            else:
                failed += 1
            completed_payloads.append(
                completed_case_dict(
                    test_result_id=tr_id,
                    test_case_id=int(cr.get("test_case_id") or 0),
                    title=str(cr.get("title") or ""),
                    status=status_str,
                    steps_total=len(cr.get("step_results") or []),
                    steps_passed=sum(
                        1 for s in (cr.get("step_results") or []) if s.get("status") == "passed"
                    ),
                    steps_failed=sum(
                        1 for s in (cr.get("step_results") or []) if s.get("status") == "failed"
                    ),
                    duration_ms=int(cr.get("duration_ms") or 0),
                    step_results=cr.get("step_results"),
                    adapted_steps=cr.get("adapted_steps"),
                    original_steps=cr.get("original_steps"),
                    agent_logs=cr.get("agent_logs"),
                    screenshot_path=cr.get("screenshot_path"),
                    ai_modified=cr.get("ai_modified"),
                )
            )

        run_row = (
            await db.execute(select(TestRun).where(TestRun.id == run_id))
        ).scalar_one_or_none()
        cancel = progress_mgr.is_cancel_requested(run_id) or state.get("cancel_requested")
        if run_row:
            run_row.passed_tests = passed
            run_row.failed_tests = failed
            run_row.skipped_tests = skipped
            run_row.completed_at = datetime.utcnow()
            if cancel:
                run_row.status = TestRunStatus.CANCELLED
            elif failed > 0:
                run_row.status = TestRunStatus.FAILED
            else:
                run_row.status = TestRunStatus.PASSED
        await db.commit()

    terminal = "cancelled" if cancel else ("failed" if failed else "passed")
    progress_mgr.set(
        run_id,
        {
            "status": terminal,
            "percentage": 100,
            "completed_results": completed_payloads,
            "active_lanes": [],
            "groups": state.get("group_table") or [],
        },
    )
    progress_mgr.clear_cancel(run_id)
    progress_mgr.schedule_cleanup(run_id, delay_seconds=600)
    return {"status": terminal, "completed_count": len(completed_payloads)}
