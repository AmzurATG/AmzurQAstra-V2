"""Normalize error text and cluster failures for analytics."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)
_WIN_PATH_RE = re.compile(r"[a-z]:\\[^ \n]+", re.I)
_NIX_PATH_RE = re.compile(r"/(?:[\w.-]+/)+[\w.-]+")


def normalize_error_signature(error_message: Optional[str], error_stack: Optional[str]) -> str:
    """
    Produce a stable signature for grouping similar failures.
    Not cryptographic — only for UX clustering.
    """
    raw = (error_message or "").strip() or ""
    if not raw and error_stack:
        lines = [ln.strip() for ln in error_stack.splitlines() if ln.strip()]
        raw = lines[0] if lines else ""
    line = raw.split("\n", 1)[0].strip()
    line = line.lower()
    line = _UUID_RE.sub("<uuid>", line)
    line = _WIN_PATH_RE.sub("<path>", line)
    line = _NIX_PATH_RE.sub("<path>", line)
    line = re.sub(r":\d+\s*$", "", line)
    line = re.sub(r"\bline\s+\d+\b", "line <n>", line)
    line = re.sub(r"\s+", " ", line).strip()
    return line[:320] if line else "unknown"


@dataclass
class _ClusterAgg:
    count: int = 0
    sample_test_case_id: Optional[int] = None
    sample_title: Optional[str] = None
    sample_screenshot: Optional[str] = None
    last_seen_run_id: int = 0


def cluster_failed_results(
    rows: Iterable[Tuple[Any, Any, Any]],
) -> List[Dict[str, Any]]:
    """
    rows: iterable of (result_orm, test_case_orm, test_run_orm)
    Only failed/error rows should be passed in.
    """
    buckets: Dict[str, _ClusterAgg] = defaultdict(_ClusterAgg)
    for res, tc, run in rows:
        sig = normalize_error_signature(res.error_message, res.error_stack)
        agg = buckets[sig]
        agg.count += 1
        if agg.sample_test_case_id is None:
            agg.sample_test_case_id = tc.id
            agg.sample_title = (tc.title or "")[:200] or f"Case #{tc.id}"
            agg.sample_screenshot = res.screenshot_path
        if run.id >= agg.last_seen_run_id:
            agg.last_seen_run_id = run.id
    out: List[Tuple[str, _ClusterAgg]] = sorted(
        buckets.items(), key=lambda x: (-x[1].count, x[0])
    )
    return [
        {
            "signature": sig,
            "count": agg.count,
            "sample_test_case_id": agg.sample_test_case_id,
            "sample_test_case_title": agg.sample_title,
            "sample_screenshot_path": agg.sample_screenshot,
            "last_seen_run_id": agg.last_seen_run_id,
        }
        for sig, agg in out
    ]
