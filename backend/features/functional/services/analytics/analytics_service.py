"""Orchestrate functional Test Report Analytics for one project + window."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.user import User
from features.functional.schemas.analytics import (
    FailureCluster,
    ProjectAnalyticsResponse,
)
from features.functional.services.analytics.access import assert_project_access
from features.functional.services.analytics.failure_clustering import cluster_failed_results
from features.functional.services.analytics.insights import (
    build_case_status_chronology,
    flaky_tests,
    slowest_tests,
    stale_tests,
    top_failing_tests,
)
from features.functional.services.analytics.metrics import (
    compute_duration_trend_kpi,
    compute_open_failure_clusters_kpi,
    compute_pass_rate_kpi,
    compute_stability_kpi,
)
from features.functional.services.analytics.repository import (
    count_cancelled_runs_in_window,
    fetch_latest_terminal_run,
    fetch_ready_cases,
    fetch_results_for_run,
    fetch_results_with_cases_for_runs,
    fetch_runs_created_between,
    terminal_runs_in_sequence,
)
from features.functional.services.analytics.trends import (
    failures_by_facet,
    latest_run_breakdown,
    pass_rate_trend_points,
)
from features.functional.db.models.test_result import TestResult


WINDOW_DAYS: Dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}


def _res_key(st: Any) -> str:
    return st.value if hasattr(st, "value") else str(st)


async def build_functional_project_analytics(
    db: AsyncSession,
    user: User,
    project_id: int,
    window_key: str,
) -> ProjectAnalyticsResponse:
    if window_key not in WINDOW_DAYS:
        raise ValueError(f"Invalid window: {window_key!r}")
    await assert_project_access(db, user, project_id)

    now = datetime.now(timezone.utc)
    days = WINDOW_DAYS[window_key]
    start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)

    runs_curr = await fetch_runs_created_between(db, project_id, start, now)
    runs_prev = await fetch_runs_created_between(db, project_id, prev_start, start)
    cancelled = await count_cancelled_runs_in_window(db, project_id, start, now)

    run_ids_window = [r.id for r in runs_curr]
    rows = await fetch_results_with_cases_for_runs(db, run_ids_window)

    case_chrono = build_case_status_chronology(rows)
    case_status_map = {cid: list(statuses) for cid, (statuses, _) in case_chrono.items()}

    kpis = [
        compute_pass_rate_kpi(runs_curr, runs_prev),
        compute_stability_kpi(case_status_map),
        compute_duration_trend_kpi(runs_curr, runs_prev),
    ]

    latest = await fetch_latest_terminal_run(db, project_id)
    latest_bd = None
    cluster_kpi_val = 0
    if latest is not None:
        res_latest = await fetch_results_for_run(db, latest.id)
        latest_bd = latest_run_breakdown(latest, res_latest, cancelled)
        rows_latest = await fetch_results_with_cases_for_runs(db, [latest.id])
        failed_only = [
            (r, tc, tr)
            for r, tc, tr in rows_latest
            if _res_key(r.status) in ("failed", "error")
        ]
        cluster_kpi_val = len(cluster_failed_results(failed_only))

    kpis.append(compute_open_failure_clusters_kpi(cluster_kpi_val))

    failed_window = [
        (r, tc, tr)
        for r, tc, tr in rows
        if _res_key(r.status) in ("failed", "error")
    ]
    cluster_dicts = cluster_failed_results(failed_window)
    failure_clusters = [FailureCluster(**c) for c in cluster_dicts[:25]]

    terminal_curr = terminal_runs_in_sequence(runs_curr)
    trend_runs = terminal_curr[-30:]
    trend_run_ids = [r.id for r in trend_runs]
    trend_rows = await fetch_results_with_cases_for_runs(db, trend_run_ids)
    results_by_run: Dict[int, List[TestResult]] = defaultdict(list)
    for r, _tc, _tr in trend_rows:
        results_by_run[r.test_run_id].append(r)
    pass_trend = pass_rate_trend_points(trend_runs, dict(results_by_run))

    cat_bars = failures_by_facet(rows, "category")
    pri_bars = failures_by_facet(rows, "priority")

    top_fail = top_failing_tests(rows)
    flaky = flaky_tests(case_chrono)
    slow = slowest_tests(rows)
    ready = await fetch_ready_cases(db, project_id)
    in_window = {tc.id for _, tc, _ in rows}
    stale = stale_tests(ready, in_window)

    return ProjectAnalyticsResponse(
        source="functional",
        window=window_key,
        kpis=kpis,
        latest_run=latest_bd,
        pass_rate_trend=pass_trend,
        failures_by_category=cat_bars,
        failures_by_priority=pri_bars,
        top_failing=top_fail,
        failure_clusters=failure_clusters,
        flaky=flaky,
        slowest=slow,
        stale=stale,
        generated_at=now,
    )
