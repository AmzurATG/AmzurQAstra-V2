"""Unit tests for analytics metrics helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from features.functional.services.analytics.metrics import (
    compute_duration_trend_kpi,
    compute_pass_rate_kpi,
    compute_stability_kpi,
)
import features.functional.db.models.test_run as _test_run_model


def _run(
    *,
    status: _test_run_model.TestRunStatus,
    started_offset_sec: float = 0,
    duration_sec: float = 120,
):
    base = datetime.now(timezone.utc)
    started = base - timedelta(seconds=started_offset_sec)
    completed = started + timedelta(seconds=duration_sec)
    return SimpleNamespace(
        status=status,
        started_at=started,
        completed_at=completed,
    )


def test_pass_rate_kpi_all_passed_vs_half():
    cur = [
        _run(status=_test_run_model.TestRunStatus.PASSED),
        _run(status=_test_run_model.TestRunStatus.PASSED),
    ]
    prev = [
        _run(status=_test_run_model.TestRunStatus.PASSED),
        _run(status=_test_run_model.TestRunStatus.FAILED),
    ]
    k = compute_pass_rate_kpi(cur, prev)
    assert k.value == "100%"
    assert k.delta == "+50%"
    assert k.trend == "up"
    assert k.higher_is_better is True


def test_stability_kpi_mixed_cases():
    case_status_map = {
        1: ["passed", "passed"],
        2: ["passed", "failed"],
        3: ["failed"],
    }
    k = compute_stability_kpi(case_status_map)
    assert k.value == "67%"
    assert k.key == "stability"


def test_duration_trend_slower_in_current_window():
    fast = _run(
        status=_test_run_model.TestRunStatus.PASSED,
        duration_sec=60,
    )
    slow = _run(
        status=_test_run_model.TestRunStatus.PASSED,
        duration_sec=120,
    )
    k = compute_duration_trend_kpi([slow], [fast])
    assert "min" in k.value
    assert k.higher_is_better is False
    assert k.trend in ("up", "flat", "down")
