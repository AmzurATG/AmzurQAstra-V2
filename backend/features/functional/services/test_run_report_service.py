"""Build a structured report for a test run (shared by in-app view + PDF)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from features.functional.core.grouping.setup_step_merger import compute_step_display_counts
from features.functional.core.case_budget import format_duration_ms
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun
from features.functional.db.models.test_run_group import TestRunGroup
from features.functional.services.report_aggregator import aggregate_groups_by_parent


def _status_str(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _case_payload(tr: TestResult) -> Dict[str, Any]:
    tc = getattr(tr, "test_case", None)
    title = (tc.title if tc else None) or f"Test Case #{tr.test_case_id}"
    steps = tr.step_results or []
    counts = compute_step_display_counts(steps)
    ai = tr.ai_modified or {}
    adaptations = [s for s in steps if s.get("adaptation")]
    dur = tr.duration_ms or 0
    status = _status_str(tr.status)
    infra = bool(ai.get("infra_error")) or status == "error"
    return {
        "test_result_id": tr.id,
        "test_case_id": tr.test_case_id,
        "title": title,
        "status": status,
        "duration_ms": dur,
        "duration_display": format_duration_ms(dur),
        "group_id": tr.group_id,
        "steps_total": counts["steps_total"],
        "steps_passed": counts["steps_passed"],
        "steps_failed": counts["steps_failed"],
        "setup_skipped_count": counts["setup_skipped_count"],
        "steps": steps,
        "has_adaptations": bool(adaptations) or bool(ai.get("has_changes")),
        "adaptation_count": len(adaptations),
        "screenshot_path": tr.screenshot_path,
        "agent_logs": tr.agent_logs or [],
        "error_message": tr.error_message,
        "user_message": ai.get("user_message"),
        "infra_error": infra,
        "ui_override": bool(ai.get("ui_override")),
        "executor_status": ai.get("executor_status"),
    }


async def build_report_data(db: AsyncSession, run_id: int) -> Optional[Dict[str, Any]]:
    """Assemble run summary + groups + per-case detail from persisted rows."""
    run = (
        await db.execute(
            select(TestRun)
            .options(selectinload(TestRun.test_results).selectinload(TestResult.test_case))
            .where(TestRun.id == run_id)
        )
    ).scalar_one_or_none()
    if not run:
        return None

    groups = list(
        (
            await db.execute(
                select(TestRunGroup).where(TestRunGroup.test_run_id == run_id)
            )
        ).scalars().all()
    )

    results = [
        r for r in (run.test_results or [])
        if _status_str(r.status) != "skipped" or (r.step_results)
    ]
    cases = [_case_payload(r) for r in sorted(results, key=lambda x: x.id)]
    cases_by_group: Dict[str, List[Dict[str, Any]]] = {}
    ungrouped: List[Dict[str, Any]] = []
    for c in cases:
        gid = c.get("group_id")
        if gid:
            cases_by_group.setdefault(gid, []).append(c)
        else:
            ungrouped.append(c)

    group_payloads: List[Dict[str, Any]] = []
    for g in groups:
        gcases = cases_by_group.get(g.group_id, [])
        group_payloads.append(
            {
                "group_id": g.group_id,
                "parent_group_id": getattr(g, "parent_group_id", None),
                "title": g.title or g.group_id,
                "phase_order": g.phase_order or [],
                "shared_login": bool(g.shared_login),
                "case_ids": g.case_ids or [],
                "cases": gcases,
                "passed": sum(1 for c in gcases if c["status"] == "passed"),
                "total": len(gcases),
            }
        )
    if ungrouped:
        group_payloads.append(
            {
                "group_id": "__ungrouped",
                "parent_group_id": None,
                "title": "Other cases",
                "phase_order": [],
                "shared_login": False,
                "case_ids": [c["test_case_id"] for c in ungrouped],
                "cases": ungrouped,
                "passed": sum(1 for c in ungrouped if c["status"] == "passed"),
                "total": len(ungrouped),
            }
        )

    themes = aggregate_groups_by_parent(group_payloads)

    cfg = run.config or {}
    total = len(cases)
    blocked_cases = [c for c in cases if c["status"] == "error" or c.get("infra_error")]
    blocked_ids = {c["test_result_id"] for c in blocked_cases}
    failed_cases = [
        c for c in cases if c["status"] == "failed" and c["test_result_id"] not in blocked_ids
    ]
    passed = sum(1 for c in cases if c["status"] == "passed")
    failed = len(failed_cases)
    blocked = len(blocked_cases)
    total_adaptations = sum(c["adaptation_count"] for c in cases)
    sum_case_ms = sum(int(c.get("duration_ms") or 0) for c in cases)
    wall_ms = 0
    if run.started_at and run.completed_at:
        try:
            wall_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        except Exception:
            wall_ms = 0
    if wall_ms <= 0:
        wall_ms = sum_case_ms

    return {
        "run_id": run.id,
        "run_number": run.run_number,
        "project_id": run.project_id,
        "name": run.name,
        "status": _status_str(run.status),
        "app_url": cfg.get("app_url"),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "lane_count": cfg.get("lane_count"),
        "health": cfg.get("health"),
        "health_summary": cfg.get("health_summary"),
        "totals": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "skipped": run.skipped_tests or 0,
            "success_rate": round((passed / total) * 100) if total else 0,
            "adaptations": total_adaptations,
            "duration_ms": wall_ms,
            "duration_display": format_duration_ms(wall_ms),
            "sum_case_duration_ms": sum_case_ms,
            "sum_case_duration_display": format_duration_ms(sum_case_ms),
        },
        "groups": group_payloads,
        "themes": themes,
        "cases": cases,
        "failed_cases": failed_cases,
        "blocked_cases": blocked_cases,
    }
