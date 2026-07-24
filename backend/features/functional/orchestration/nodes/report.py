"""Report node: persist results to Postgres and finalize run progress."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select

from features.functional.core.grouping.setup_step_merger import compute_step_display_counts
from features.functional.core.memory.store import append_event
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


def _health_block(state: OrchestrationState) -> Dict[str, Any]:
    supervisor = state.get("supervisor") or {}
    watchdog = state.get("watchdog") or {}
    llm_gate = state.get("llm_gate") or {}
    desync = list(state.get("ui_desync_events") or [])
    reassigns = list(watchdog.get("reassign_events") or [])
    breaker = (llm_gate.get("breaker") or {}) if isinstance(llm_gate, dict) else {}
    return {
        "lanes_expected": supervisor.get("lanes_expected"),
        "lanes_ready": supervisor.get("lanes_ready"),
        "reassign_count": len(reassigns),
        "circuit_open": bool(breaker.get("state") == "open" or breaker.get("budget_exhausted")),
        "ui_desync_events": len(desync),
        "recon_ok": bool((state.get("recon_cache") or {}).get("ok")) if state.get("recon_cache") else None,
    }


def _health_summary(health: Dict[str, Any]) -> str:
    parts = [
        f"lanes {health.get('lanes_ready')}/{health.get('lanes_expected')}",
        f"reassigns {health.get('reassign_count') or 0}",
        f"ui_desync {health.get('ui_desync_events') or 0}",
    ]
    if health.get("circuit_open"):
        parts.append("LLM circuit opened during run")
    return "Run health: " + "; ".join(parts) + "."


async def report_node(state: OrchestrationState, *, db_session_factory) -> Dict[str, Any]:
    """Persist case results. db_session_factory injected at invoke time."""
    run_id = int(state["run_id"])
    progress_mgr = RunProgressManager()
    results: List[CaseResult] = list(state.get("case_results") or [])
    retry_map = {int(r["test_case_id"]): r for r in (state.get("retry_results") or [])}
    for cid, rr in retry_map.items():
        results = [r for r in results if int(r.get("test_case_id") or 0) != cid]
        results.append(rr)

    completed_payloads: List[Dict[str, Any]] = []
    passed = failed = skipped = 0
    health = _health_block(state)
    health_text = _health_summary(health)

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
            counts = compute_step_display_counts(cr.get("step_results") or [])
            completed_payloads.append(
                completed_case_dict(
                    test_result_id=tr_id,
                    test_case_id=int(cr.get("test_case_id") or 0),
                    title=str(cr.get("title") or ""),
                    status=status_str,
                    steps_total=counts["steps_total"],
                    steps_passed=counts["steps_passed"],
                    steps_failed=counts["steps_failed"],
                    setup_skipped_count=counts["setup_skipped_count"],
                    duration_ms=int(cr.get("duration_ms") or 0),
                    step_results=cr.get("step_results"),
                    adapted_steps=cr.get("adapted_steps"),
                    original_steps=cr.get("original_steps"),
                    agent_logs=cr.get("agent_logs"),
                    screenshot_path=cr.get("screenshot_path"),
                    ai_modified=cr.get("ai_modified"),
                    ui_override=bool(cr.get("ui_override")),
                    ui_validation=cr.get("ui_validation"),
                    executor_status=cr.get("executor_status"),
                    verdict_source=cr.get("verdict_source"),
                )
            )

        run_row = (
            await db.execute(select(TestRun).where(TestRun.id == run_id))
        ).scalar_one_or_none()
        cancel = progress_mgr.is_cancel_requested(run_id) or state.get("cancel_requested")
        paused = bool(state.get("paused"))
        pause_reason = str(state.get("pause_reason") or "")
        if run_row:
            run_row.passed_tests = passed
            run_row.failed_tests = failed
            run_row.skipped_tests = skipped
            run_row.completed_at = datetime.utcnow()
            cfg = dict(run_row.config or {})
            cfg["health"] = health
            cfg["health_summary"] = health_text
            if cancel:
                run_row.status = TestRunStatus.CANCELLED
            elif paused:
                run_row.status = TestRunStatus.CANCELLED
                cfg.update(
                    {
                        "paused": True,
                        "pause_reason": pause_reason,
                        "resumable": True,
                        "llm_gate": state.get("llm_gate"),
                    }
                )
            elif state.get("status") == "error" and not results:
                run_row.status = TestRunStatus.FAILED
            elif failed > 0:
                run_row.status = TestRunStatus.FAILED
            else:
                run_row.status = TestRunStatus.PASSED
            run_row.config = cfg
        await db.commit()

    project_id = int(state.get("project_id") or 0)
    if project_id and health.get("reassign_count"):
        append_event(
            project_id,
            {"type": "run_health", "run_id": run_id, "health": health},
            hint=health_text,
        )

    live = progress_mgr.get(run_id) or {}
    terminal = (
        "error" if (state.get("status") == "error" and not results)
        else ("paused" if paused else ("cancelled" if cancel else ("failed" if failed else "passed")))
    )
    progress_mgr.set(
        run_id,
        {
            "status": terminal,
            "percentage": 100,
            "completed_results": completed_payloads,
            "active_lanes": [],
            "groups": state.get("group_table") or [],
            "current_step_info": (
                f"Paused — {pause_reason}. Resume when the LLM proxy recovers."
                if paused
                else (state.get("error") or health_text)
            ),
            "llm_gate": state.get("llm_gate"),
            "health": health,
            "health_summary": health_text,
            "ui_desync": bool(live.get("ui_desync")),
            "ui_desync_events": list(state.get("ui_desync_events") or live.get("ui_desync_events") or []),
            "supervisor": state.get("supervisor"),
            "error": state.get("error"),
        },
    )
    progress_mgr.clear_cancel(run_id)
    progress_mgr.schedule_cleanup(run_id, delay_seconds=600)
    return {
        "status": terminal,
        "completed_count": len(completed_payloads),
        "health": health,
    }
