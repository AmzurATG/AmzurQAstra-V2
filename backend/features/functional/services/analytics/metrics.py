"""KPI computations from run lists and status histories."""

from __future__ import annotations

from typing import List, Optional, Tuple

from features.functional.schemas.analytics import KpiPoint
from features.functional.db.models.test_run import TestRun
from features.functional.services.analytics.repository import (
    run_duration_seconds,
    terminal_runs_in_sequence,
)


def _fmt_pct(x: float) -> str:
    return f"{round(x)}%"


def _delta_pct(cur: float, prev: float) -> Tuple[Optional[str], str]:
    d = cur - prev
    if abs(d) < 0.05:
        return None, "flat"
    sym = "+" if d > 0 else ""
    return f"{sym}{round(d)}%", "up" if d > 0 else "down"


def compute_pass_rate_kpi(
    runs_current: List[TestRun],
    runs_previous: List[TestRun],
) -> KpiPoint:
    tc = terminal_runs_in_sequence(runs_current)
    tp = terminal_runs_in_sequence(runs_previous)
    cur = (
        sum(1 for r in tc if r.status == "passed") / len(tc) * 100 if tc else 0.0
    )
    prev = (
        sum(1 for r in tp if r.status == "passed") / len(tp) * 100 if tp else 0.0
    )
    delta_str, trend = _delta_pct(cur, prev)
    return KpiPoint(
        key="pass_rate",
        label="Pass rate",
        value=_fmt_pct(cur),
        delta=delta_str,
        trend=trend,  # type: ignore[arg-type]
        higher_is_better=True,
        help="Share of finished runs that passed in this window (excludes pending/running).",
    )


def compute_stability_kpi(case_status_map: dict[int, List[str]]) -> KpiPoint:
    active = {k: v for k, v in case_status_map.items() if v}
    if not active:
        return KpiPoint(
            key="stability",
            label="Stability",
            value="–",
            delta=None,
            trend="flat",
            higher_is_better=True,
            help="Share of test cases with no status changes in this window.",
        )
    stable = sum(1 for statuses in active.values() if len(set(statuses)) <= 1)
    pct = stable / len(active) * 100
    return KpiPoint(
        key="stability",
        label="Stability",
        value=_fmt_pct(pct),
        delta=None,
        trend="flat",
        higher_is_better=True,
        help="Share of test cases that did not change status across runs this window.",
    )


def compute_duration_trend_kpi(
    runs_current: List[TestRun],
    runs_previous: List[TestRun],
) -> KpiPoint:
    tc = [r for r in terminal_runs_in_sequence(runs_current) if r.status != "cancelled"]
    tp = [r for r in terminal_runs_in_sequence(runs_previous) if r.status != "cancelled"]

    def avg_sec(runs: List[TestRun]) -> Optional[float]:
        secs = [run_duration_seconds(r) for r in runs]
        secs = [s for s in secs if s is not None and s >= 0]
        return sum(secs) / len(secs) if secs else None

    cur_m = avg_sec(tc)
    prev_m = avg_sec(tp)
    if cur_m is None:
        return KpiPoint(
            key="avg_duration",
            label="Avg run duration",
            value="–",
            delta=None,
            trend="flat",
            higher_is_better=False,
            help="Mean wall-clock duration of finished runs (cancelled excluded).",
        )
    cur_min = cur_m / 60.0
    val = f"{cur_min:.1f} min"
    if prev_m is None or prev_m <= 0:
        return KpiPoint(
            key="avg_duration",
            label="Avg run duration",
            value=val,
            delta=None,
            trend="flat",
            higher_is_better=False,
            help="Mean wall-clock duration of finished runs vs prior window.",
        )
    delta_ratio = (cur_m - prev_m) / prev_m * 100
    if abs(delta_ratio) < 1:
        trend: str = "flat"
        dstr = None
    elif delta_ratio > 0:
        trend = "up"
        dstr = f"+{round(delta_ratio)}%"
    else:
        trend = "down"
        dstr = f"{round(delta_ratio)}%"
    return KpiPoint(
        key="avg_duration",
        label="Avg run duration",
        value=val,
        delta=dstr,
        trend=trend,  # type: ignore[arg-type]
        higher_is_better=False,
        help="Mean wall-clock duration of finished runs vs prior window. Lower is better.",
    )


def compute_open_failure_clusters_kpi(cluster_count: int) -> KpiPoint:
    return KpiPoint(
        key="open_failure_clusters",
        label="Failure clusters",
        value=str(cluster_count),
        delta=None,
        trend="flat",
        higher_is_better=False,
        help="Distinct failure signatures in the latest run (grouped from error text).",
    )
