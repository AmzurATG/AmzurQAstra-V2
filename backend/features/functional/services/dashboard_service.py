"""Aggregate dashboard metrics across projects visible to the current user."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from common.db.models.project import Project
from common.db.models.user import User
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_run import TestRun


async def _accessible_project_ids(db: AsyncSession, user: User) -> List[int]:
    q = select(Project.id).where(Project.is_active == True)  # noqa: E712
    if not user.is_superuser:
        q = q.where(Project.owner_id == user.id)
    rows = (await db.execute(q)).all()
    return [r[0] for r in rows]


def _status_key(st: Any) -> str:
    if hasattr(st, "value"):
        return str(st.value)
    return str(st)


def _aggregate_run_counts(rows: List[Tuple[Any, int]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for st, n in rows:
        key = _status_key(st)
        counts[key] = n

    total = sum(counts.values())
    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0) + counts.get("error", 0)
    running = counts.get("running", 0)
    pending = counts.get("pending", 0)
    cancelled = counts.get("cancelled", 0)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "running": running,
        "pending": pending,
        "cancelled": cancelled,
        "avg_pass_rate": round((passed / total) * 100) if total else 0,
    }


async def fetch_dashboard_overview(db: AsyncSession, user: User) -> Dict[str, Any]:
    ids = await _accessible_project_ids(db, user)
    project_count = len(ids)

    if not ids:
        day_keys_empty = [(datetime.now(timezone.utc).date() - timedelta(days=i)) for i in range(6, -1, -1)]
        activity = [
            {"date": d.isoformat(), "passed": 0, "failed": 0, "other": 0}
            for d in day_keys_empty
        ]
        return {
            "project_count": 0,
            "test_cases_total": 0,
            "runs_total": 0,
            "runs_passed": 0,
            "runs_failed": 0,
            "runs_running": 0,
            "runs_pending": 0,
            "runs_cancelled": 0,
            "avg_pass_rate": 0,
            "recent_runs": [],
            "recent_projects": [],
            "activity_by_day": activity,
        }

    # Test cases
    tc_q = select(func.count(TestCase.id)).where(TestCase.project_id.in_(ids))
    test_cases_total = (await db.execute(tc_q)).scalar() or 0

    # Run status aggregates (all time)
    run_grp = (
        select(TestRun.status, func.count(TestRun.id))
        .where(TestRun.project_id.in_(ids))
        .group_by(TestRun.status)
    )
    run_rows = (await db.execute(run_grp)).all()
    agg = _aggregate_run_counts(run_rows)

    # Recent runs with project name
    p = aliased(Project)
    recent_q = (
        select(TestRun, p.name)
        .join(p, TestRun.project_id == p.id)
        .where(TestRun.project_id.in_(ids))
        .order_by(TestRun.created_at.desc())
        .limit(8)
    )
    recent_result = await db.execute(recent_q)
    recent_runs = []
    for run, project_name in recent_result.all():
        st = _status_key(run.status)
        recent_runs.append(
            {
                "id": run.id,
                "project_id": run.project_id,
                "project_name": project_name,
                "name": run.name,
                "description": run.description,
                "status": st,
                "created_at": run.created_at,
            }
        )

    # Recent projects
    rp_q = (
        select(Project)
        .where(Project.id.in_(ids))
        .order_by(Project.updated_at.desc())
        .limit(5)
    )
    rp_rows = (await db.execute(rp_q)).scalars().all()
    recent_projects = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "updated_at": p.updated_at,
        }
        for p in rp_rows
    ]

    # Activity: last 7 calendar days (UTC), runs created per day
    today = datetime.now(timezone.utc).date()
    day_keys = [today - timedelta(days=i) for i in range(6, -1, -1)]
    start_dt = datetime.combine(day_keys[0], datetime.min.time(), tzinfo=timezone.utc)

    act_q = select(TestRun.created_at, TestRun.status).where(
        TestRun.project_id.in_(ids),
        TestRun.created_at >= start_dt,
    )
    act_rows = (await db.execute(act_q)).all()

    buckets: Dict[Any, Dict[str, int]] = {
        d: {"passed": 0, "failed": 0, "other": 0} for d in day_keys
    }
    for created_at, status in act_rows:
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        d = created_at.date()
        if d not in buckets:
            continue
        sk = _status_key(status)
        if sk == "passed":
            buckets[d]["passed"] += 1
        elif sk in ("failed", "error"):
            buckets[d]["failed"] += 1
        else:
            buckets[d]["other"] += 1

    activity_by_day = [
        {
            "date": d.isoformat(),
            "passed": buckets[d]["passed"],
            "failed": buckets[d]["failed"],
            "other": buckets[d]["other"],
        }
        for d in day_keys
    ]

    return {
        "project_count": project_count,
        "test_cases_total": test_cases_total,
        "runs_total": agg["total"],
        "runs_passed": agg["passed"],
        "runs_failed": agg["failed"],
        "runs_running": agg["running"],
        "runs_pending": agg["pending"],
        "runs_cancelled": agg["cancelled"],
        "avg_pass_rate": agg["avg_pass_rate"],
        "recent_runs": recent_runs,
        "recent_projects": recent_projects,
        "activity_by_day": activity_by_day,
    }
