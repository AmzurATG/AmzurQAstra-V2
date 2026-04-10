"""Dashboard aggregate API schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DashboardRecentRunItem(BaseModel):
    id: int
    project_id: int
    project_name: str
    name: Optional[str] = None
    description: Optional[str] = None
    status: str
    created_at: datetime


class DashboardRecentProjectItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    updated_at: datetime


class DashboardActivityDay(BaseModel):
    """Counts of test runs created on this calendar day (UTC)."""

    date: str  # YYYY-MM-DD
    passed: int
    failed: int
    other: int


class DashboardOverviewResponse(BaseModel):
    project_count: int
    test_cases_total: int
    runs_total: int
    runs_passed: int
    runs_failed: int
    runs_running: int
    runs_pending: int
    runs_cancelled: int
    avg_pass_rate: int
    recent_runs: List[DashboardRecentRunItem]
    recent_projects: List[DashboardRecentProjectItem]
    activity_by_day: List[DashboardActivityDay]
