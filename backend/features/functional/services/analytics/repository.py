"""Read-only queries for functional test analytics."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.db.models.test_case import TestCase, TestCaseStatus
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun, TestRunStatus


TERMINAL_RUN_STATUSES: Tuple[TestRunStatus, ...] = (
    TestRunStatus.PASSED,
    TestRunStatus.FAILED,
    TestRunStatus.ERROR,
    TestRunStatus.CANCELLED,
)


async def fetch_runs_created_between(
    db: AsyncSession,
    project_id: int,
    start: datetime,
    end: datetime,
) -> List[TestRun]:
    q = (
        select(TestRun)
        .where(
            TestRun.project_id == project_id,
            TestRun.created_at >= start,
            TestRun.created_at < end,
        )
        .order_by(TestRun.run_number.asc())
    )
    return list((await db.execute(q)).scalars().all())


async def fetch_latest_terminal_run(
    db: AsyncSession, project_id: int
) -> Optional[TestRun]:
    q = (
        select(TestRun)
        .where(
            TestRun.project_id == project_id,
            TestRun.status.in_(TERMINAL_RUN_STATUSES),
        )
        .order_by(TestRun.run_number.desc())
        .limit(1)
    )
    return (await db.execute(q)).scalar_one_or_none()


async def fetch_results_for_run(
    db: AsyncSession, run_id: int
) -> List[TestResult]:
    q = (
        select(TestResult)
        .where(TestResult.test_run_id == run_id)
        .order_by(TestResult.id.asc())
    )
    return list((await db.execute(q)).scalars().all())


async def fetch_results_with_cases_for_runs(
    db: AsyncSession, run_ids: Sequence[int]
) -> List[Tuple[TestResult, TestCase, TestRun]]:
    if not run_ids:
        return []
    q = (
        select(TestResult, TestCase, TestRun)
        .join(TestRun, TestResult.test_run_id == TestRun.id)
        .join(TestCase, TestResult.test_case_id == TestCase.id)
        .where(TestResult.test_run_id.in_(run_ids))
        .order_by(TestRun.run_number.asc(), TestResult.id.asc())
    )
    rows = (await db.execute(q)).all()
    return [(r, tc, tr) for r, tc, tr in rows]


async def fetch_ready_cases(db: AsyncSession, project_id: int) -> List[TestCase]:
    q = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.status == TestCaseStatus.ready,
    )
    return list((await db.execute(q)).scalars().all())


async def count_cancelled_runs_in_window(
    db: AsyncSession,
    project_id: int,
    window_start: datetime,
    now: datetime,
) -> int:
    q = select(TestRun).where(
        TestRun.project_id == project_id,
        TestRun.status == TestRunStatus.CANCELLED,
        TestRun.created_at >= window_start,
        TestRun.created_at < now,
    )
    rows = (await db.execute(q)).scalars().all()
    return len(rows)


def terminal_runs_in_sequence(runs: List[TestRun]) -> List[TestRun]:
    return [r for r in runs if r.status in TERMINAL_RUN_STATUSES]


def run_duration_seconds(run: TestRun) -> Optional[float]:
    if run.started_at is None or run.completed_at is None:
        return None
    return (run.completed_at - run.started_at).total_seconds()
