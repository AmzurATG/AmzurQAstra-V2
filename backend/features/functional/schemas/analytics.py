"""Pydantic models for project Test Report Analytics (functional scope v1)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class KpiPoint(BaseModel):
    """Single KPI tile: formatted value + trend vs prior window."""

    key: str
    label: str
    value: str = Field(description="Human-readable primary value")
    delta: Optional[str] = Field(None, description="Change vs previous window, e.g. +3%")
    trend: Literal["up", "down", "flat"] = "flat"
    higher_is_better: bool = Field(
        True,
        description="If True, trend 'up' is good (green); if False, 'down' is good.",
    )
    help: str = Field("", description="Short explanation for tooltip")


class LatestRunBreakdown(BaseModel):
    """Result-level snapshot for the latest terminal run (donut chart)."""

    run_id: int
    run_number: int
    passed: int = 0
    failed: int = 0
    not_executed: int = Field(0, description="Skipped results in this run")
    error: int = 0
    cancelled_runs_in_window: int = Field(
        0, description="Runs with status cancelled in the analytics window"
    )


class TrendPoint(BaseModel):
    """One point on the pass-rate-over-runs line chart."""

    x: str = Field(description="Label, usually run number as string")
    run_id: int
    run_number: int
    value: float = Field(description="Result pass rate 0-100 for this run")


class BarPoint(BaseModel):
    """Stacked bar row for category or priority."""

    facet_value: str
    passed: int = 0
    failed: int = 0
    not_executed: int = 0
    error: int = 0


class FailureCluster(BaseModel):
    """Deduped failure signature from error messages / stack."""

    signature: str
    count: int
    sample_test_case_id: Optional[int] = None
    sample_test_case_title: Optional[str] = None
    sample_screenshot_path: Optional[str] = None
    last_seen_run_id: int


class TopFailingTest(BaseModel):
    """Row for top failing tests card with sparkline data."""

    test_case_id: int
    title: str
    fail_count: int
    recent_statuses: List[str] = Field(
        default_factory=list,
        description="Most recent statuses for micro sparkline (oldest -> newest)",
    )
    latest_run_id: Optional[int] = None


class FlakyTest(BaseModel):
    test_case_id: int
    title: str
    flips: int
    last_status: str


class SlowTest(BaseModel):
    test_case_id: int
    title: str
    p95_ms: int
    runs_used: int


class StaleTest(BaseModel):
    test_case_id: int
    title: str
    last_executed_at: Optional[datetime] = None


class ProjectAnalyticsResponse(BaseModel):
    """Bundled analytics for one project + source + time window."""

    source: str
    window: str
    kpis: List[KpiPoint]
    latest_run: Optional[LatestRunBreakdown] = None
    pass_rate_trend: List[TrendPoint] = Field(default_factory=list)
    failures_by_category: List[BarPoint] = Field(default_factory=list)
    failures_by_priority: List[BarPoint] = Field(default_factory=list)
    top_failing: List[TopFailingTest] = Field(default_factory=list)
    failure_clusters: List[FailureCluster] = Field(default_factory=list)
    flaky: List[FlakyTest] = Field(default_factory=list)
    slowest: List[SlowTest] = Field(default_factory=list)
    stale: List[StaleTest] = Field(default_factory=list)
    generated_at: datetime
