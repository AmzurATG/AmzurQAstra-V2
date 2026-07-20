"""Shared per-case result persistence for orchestrated runs.

Enables incremental writes so the UI can show each test case's verdict and
screenshots as soon as it finishes, instead of only at the end of the run.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import select

from common.db.database import async_session_maker
from common.utils.logger import logger
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.orchestration.state import CaseResult
from features.functional.services.completed_result_builder import completed_case_dict

STATUS_MAP = {
    "passed": TestResultStatus.PASSED,
    "failed": TestResultStatus.FAILED,
    "error": TestResultStatus.ERROR,
    "cancelled": TestResultStatus.SKIPPED,
    "skipped": TestResultStatus.SKIPPED,
}


def case_result_to_completed_dict(cr: CaseResult) -> Dict[str, Any]:
    """Shape a CaseResult into the CompletedCaseResult dict the live UI expects."""
    step_results = cr.get("step_results") or []
    d = completed_case_dict(
        test_result_id=int(cr.get("test_result_id") or 0),
        test_case_id=int(cr.get("test_case_id") or 0),
        title=str(cr.get("title") or ""),
        status=str(cr.get("status") or "error"),
        steps_total=len(step_results),
        steps_passed=sum(1 for s in step_results if s.get("status") == "passed"),
        steps_failed=sum(1 for s in step_results if s.get("status") == "failed"),
        duration_ms=int(cr.get("duration_ms") or 0),
        step_results=step_results,
        adapted_steps=cr.get("adapted_steps"),
        original_steps=cr.get("original_steps"),
        agent_logs=cr.get("agent_logs"),
        screenshot_path=cr.get("screenshot_path"),
        ai_modified=cr.get("ai_modified"),
    )
    d["group_id"] = cr.get("group_id")
    return d


async def persist_single_result(cr: CaseResult) -> None:
    """Write one finished case to its TestResult row immediately."""
    tr_id = int(cr.get("test_result_id") or 0)
    if not tr_id:
        return
    status_str = str(cr.get("status") or "error")
    db_status = STATUS_MAP.get(status_str, TestResultStatus.ERROR)
    try:
        async with async_session_maker() as db:
            row = (
                await db.execute(select(TestResult).where(TestResult.id == tr_id))
            ).scalar_one_or_none()
            if not row:
                return
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
            await db.commit()
    except Exception as exc:
        logger.warning("[ResultPersistence] tr_id=%s persist failed: %s", tr_id, exc)
