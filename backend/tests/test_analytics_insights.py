"""Unit tests for flaky / top-failing / stale insights."""

from __future__ import annotations

from types import SimpleNamespace

from features.functional.services.analytics.insights import (
    build_case_status_chronology,
    flaky_tests,
    stale_tests,
    top_failing_tests,
)


def _row(status: str, case_id: int, title: str, run_num: int, run_id: int, rid: int):
    return (
        SimpleNamespace(status=status, id=rid, test_run_id=run_id, duration_ms=1000),
        SimpleNamespace(id=case_id, title=title),
        SimpleNamespace(run_number=run_num, id=run_id),
    )


def test_top_failing_orders_by_count():
    rows = [
        _row("failed", 1, "A", 1, 100, 1),
        _row("passed", 1, "A", 2, 101, 2),
        _row("failed", 2, "B", 1, 100, 3),
        _row("failed", 2, "B", 2, 101, 4),
        _row("failed", 2, "B", 3, 102, 5),
    ]
    top = top_failing_tests(rows, top=5)
    assert top[0].test_case_id == 2
    assert top[0].fail_count == 3


def test_flaky_requires_two_flips_in_last_ten():
    chrono = {
        1: (["passed", "failed", "passed", "failed"], "Flipper"),
        2: (["passed", "passed", "failed"], "Stable mostly"),
    }
    flaky = flaky_tests(chrono, top=5)
    assert any(f.test_case_id == 1 for f in flaky)
    assert all(f.test_case_id != 2 for f in flaky)


def test_stale_not_in_window():
    ready = [SimpleNamespace(id=10, title="Old"), SimpleNamespace(id=20, title="Ran")]
    in_window = {20}
    stale = stale_tests(ready, in_window)
    assert len(stale) == 1
    assert stale[0].test_case_id == 10


def test_build_case_status_chronology_sorts_by_run():
    rows = [
        _row("failed", 1, "A", 2, 101, 1),
        _row("passed", 1, "A", 1, 100, 2),
    ]
    ch = build_case_status_chronology(rows)
    assert ch[1][0] == ["passed", "failed"]
