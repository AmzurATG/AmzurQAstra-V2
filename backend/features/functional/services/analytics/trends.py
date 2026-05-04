"""Trends and distributions for charts."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Literal, Tuple

from features.functional.schemas.analytics import BarPoint, LatestRunBreakdown, TrendPoint
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun


def _res_key(st) -> str:
    return st.value if hasattr(st, "value") else str(st)


def latest_run_breakdown(
    run: TestRun,
    results: List[TestResult],
    cancelled_runs_in_window: int,
) -> LatestRunBreakdown:
    p = f = sk = e = 0
    for r in results:
        k = _res_key(r.status)
        if k == "passed":
            p += 1
        elif k == "failed":
            f += 1
        elif k == "skipped":
            sk += 1
        elif k == "error":
            e += 1
    return LatestRunBreakdown(
        run_id=run.id,
        run_number=run.run_number,
        passed=p,
        failed=f,
        not_executed=sk,
        error=e,
        cancelled_runs_in_window=cancelled_runs_in_window,
    )


def pass_rate_trend_points(
    runs: List[TestRun],
    results_by_run: Dict[int, List[TestResult]],
    max_points: int = 30,
) -> List[TrendPoint]:
    """runs: terminal runs in chronological order (ascending run_number)."""
    if not runs:
        return []
    tail = runs[-max_points:]
    out: List[TrendPoint] = []
    for run in tail:
        res_list = results_by_run.get(run.id, [])
        if not res_list:
            out.append(
                TrendPoint(
                    x=str(run.run_number),
                    run_id=run.id,
                    run_number=run.run_number,
                    value=0.0,
                )
            )
            continue
        passed = sum(1 for r in res_list if _res_key(r.status) == "passed")
        value = passed / len(res_list) * 100.0
        out.append(
            TrendPoint(
                x=str(run.run_number),
                run_id=run.id,
                run_number=run.run_number,
                value=round(value, 1),
            )
        )
    return out


def failures_by_facet(
    rows: List[Tuple[TestResult, object, TestRun]],
    facet: Literal["category", "priority"],
) -> List[BarPoint]:
    buckets: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"passed": 0, "failed": 0, "not_executed": 0, "error": 0}
    )
    for res, tc, _ in rows:
        raw = getattr(tc, facet, None)
        key = raw.value if raw is not None and hasattr(raw, "value") else str(raw or "unknown")
        b = buckets[key]
        k = _res_key(res.status)
        if k == "passed":
            b["passed"] += 1
        elif k == "failed":
            b["failed"] += 1
        elif k == "skipped":
            b["not_executed"] += 1
        elif k == "error":
            b["error"] += 1
    ordered = sorted(buckets.keys())
    return [
        BarPoint(
            facet_value=k,
            passed=buckets[k]["passed"],
            failed=buckets[k]["failed"],
            not_executed=buckets[k]["not_executed"],
            error=buckets[k]["error"],
        )
        for k in ordered
    ]
