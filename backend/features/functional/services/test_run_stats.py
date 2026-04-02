"""Aggregate test run counts per project (for dashboard cards)."""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.db.models.test_run import TestRun


async def fetch_test_run_summary(db: AsyncSession, project_id: int) -> Dict[str, Any]:
    q = (
        select(TestRun.status, func.count(TestRun.id))
        .where(TestRun.project_id == project_id)
        .group_by(TestRun.status)
    )
    rows = (await db.execute(q)).all()
    counts: Dict[str, int] = {}
    for st, n in rows:
        key = st.value if hasattr(st, "value") else str(st)
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
