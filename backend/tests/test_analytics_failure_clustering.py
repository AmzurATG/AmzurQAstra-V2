"""Unit tests for failure signature normalization and clustering."""

from __future__ import annotations

from types import SimpleNamespace

from features.functional.services.analytics.failure_clustering import (
    cluster_failed_results,
    normalize_error_signature,
)


def test_normalize_strips_uuid_and_paths():
    msg = "Error: failed at 550e8400-e29b-41d4-a716-446655440000 in C:\\build\\app.py:42"
    sig = normalize_error_signature(msg, None)
    assert "<uuid>" in sig
    assert "<path>" in sig or "c:" not in sig


def test_cluster_groups_same_message():
    def res(msg, tc_id, run_id, ss=None):
        return (
            SimpleNamespace(
                error_message=msg,
                error_stack=None,
                screenshot_path=ss,
            ),
            SimpleNamespace(id=tc_id, title=f"TC{tc_id}"),
            SimpleNamespace(id=run_id),
        )

    rows = [
        res("Timeout waiting for login", 1, 10),
        res("Timeout waiting for login", 2, 10),
        res("Different error", 3, 11),
    ]
    clusters = cluster_failed_results(rows)
    assert len(clusters) == 2
    by_sig = {c["signature"]: c["count"] for c in clusters}
    assert by_sig[normalize_error_signature("Timeout waiting for login", None)] == 2
