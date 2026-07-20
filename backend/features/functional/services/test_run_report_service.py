"""Build a structured report for a test run (shared by in-app view + PDF)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun
from features.functional.db.models.test_run_group import TestRunGroup


def _status_str(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _case_payload(tr: TestResult) -> Dict[str, Any]:
    tc = getattr(tr, "test_case", None)
    title = (tc.title if tc else None) or f"Test Case #{tr.test_case_id}"
    steps = tr.step_results or []
    steps_passed = sum(1 for s in steps if s.get("status") == "passed")
    steps_failed = sum(1 for s in steps if s.get("status") == "failed")
    ai = tr.ai_modified or {}
    adaptations = [s for s in steps if s.get("adaptation")]
    return {
        "test_result_id": tr.id,
        "test_case_id": tr.test_case_id,
        "title": title,
        "status": _status_str(tr.status),
        "duration_ms": tr.duration_ms or 0,
        "group_id": tr.group_id,
        "steps_total": len(steps),
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "steps": steps,
        "has_adaptations": bool(adaptations) or bool(ai.get("has_changes")),
        "adaptation_count": len(adaptations),
        "screenshot_path": tr.screenshot_path,
        "agent_logs": tr.agent_logs or [],
        "error_message": tr.error_message,
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
                "title": "Other cases",
                "phase_order": [],
                "shared_login": False,
                "case_ids": [c["test_case_id"] for c in ungrouped],
                "cases": ungrouped,
                "passed": sum(1 for c in ungrouped if c["status"] == "passed"),
                "total": len(ungrouped),
            }
        )

    cfg = run.config or {}
    total = len(cases)
    passed = sum(1 for c in cases if c["status"] == "passed")
    failed = sum(1 for c in cases if c["status"] in ("failed", "error"))
    total_adaptations = sum(c["adaptation_count"] for c in cases)

    return {
        "run_id": run.id,
        "run_number": run.run_number,
        "project_id": run.project_id,
        "name": run.name,
        "status": _status_str(run.status),
        "app_url": cfg.get("app_url"),
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "lane_count": cfg.get("lane_count"),
        "totals": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": run.skipped_tests or 0,
            "success_rate": round((passed / total) * 100) if total else 0,
            "adaptations": total_adaptations,
        },
        "groups": group_payloads,
        "cases": cases,
        "failed_cases": [c for c in cases if c["status"] in ("failed", "error")],
    }
