"""Insight lists: top failures, flaky, slow, stale."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from features.functional.schemas.analytics import (
    FlakyTest,
    SlowTest,
    StaleTest,
    TopFailingTest,
)
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun


def _res_key(st) -> str:
    return st.value if hasattr(st, "value") else str(st)


def build_case_status_chronology(
    rows: List[Tuple[TestResult, TestCase, TestRun]],
) -> Dict[int, Tuple[List[str], str]]:
    """
    Returns test_case_id -> (chronological statuses as strings, title)
    """
    by_case: Dict[int, List[Tuple[int, str]]] = defaultdict(list)
    titles: Dict[int, str] = {}
    for res, tc, run in rows:
        by_case[tc.id].append((run.run_number, _res_key(res.status)))
        titles[tc.id] = tc.title or f"Case #{tc.id}"
    out: Dict[int, Tuple[List[str], str]] = {}
    for cid, pairs in by_case.items():
        pairs.sort(key=lambda x: (x[0], x[1]))
        out[cid] = ([p[1] for p in pairs], titles[cid])
    return out


def top_failing_tests(
    rows: List[Tuple[TestResult, TestCase, TestRun]],
    top: int = 5,
) -> List[TopFailingTest]:
    by_case: Dict[int, List[Tuple[int, int, TestResult, str]]] = defaultdict(list)
    titles: Dict[int, str] = {}
    for res, tc, run in rows:
        titles[tc.id] = tc.title or f"Case #{tc.id}"
        by_case[tc.id].append((run.run_number, res.id, res, _res_key(res.status)))
    fails: List[TopFailingTest] = []
    for cid, lst in by_case.items():
        lst.sort(key=lambda x: (x[0], x[1]))
        fc = sum(1 for _, _, r, _ in lst if _res_key(r.status) in ("failed", "error"))
        if fc == 0:
            continue
        statuses = [x[3] for x in lst]
        recent = statuses[-3:] if len(statuses) >= 3 else statuses
        last_run_id: Optional[int] = None
        for run_number, _rid, res, st in reversed(lst):
            if st in ("failed", "error"):
                last_run_id = res.test_run_id
                break
        fails.append(
            TopFailingTest(
                test_case_id=cid,
                title=titles[cid],
                fail_count=fc,
                recent_statuses=recent,
                latest_run_id=last_run_id,
            )
        )
    fails.sort(key=lambda x: (-x.fail_count, x.title.lower()))
    return fails[:top]


def count_status_flips(statuses: List[str]) -> int:
    if len(statuses) < 2:
        return 0
    return sum(1 for i in range(1, len(statuses)) if statuses[i] != statuses[i - 1])


def flaky_tests(case_chrono: Dict[int, Tuple[List[str], str]], top: int = 5) -> List[FlakyTest]:
    out: List[FlakyTest] = []
    for cid, (statuses, title) in case_chrono.items():
        window = statuses[-10:] if len(statuses) > 10 else statuses
        flips = count_status_flips(window)
        if flips >= 2:
            out.append(
                FlakyTest(
                    test_case_id=cid,
                    title=title,
                    flips=flips,
                    last_status=statuses[-1] if statuses else "unknown",
                )
            )
    out.sort(key=lambda x: (-x.flips, x.title.lower()))
    return out[:top]


def _p95(values: List[int]) -> int:
    if not values:
        return 0
    s = sorted(values)
    idx = min(len(s) - 1, int(round(0.95 * (len(s) - 1))))
    return int(s[idx])


def slowest_tests(
    rows: List[Tuple[TestResult, TestCase, TestRun]],
    top: int = 10,
) -> List[SlowTest]:
    by_case: Dict[int, List[int]] = defaultdict(list)
    titles: Dict[int, str] = {}
    for res, tc, _ in rows:
        if res.duration_ms is None:
            continue
        by_case[tc.id].append(res.duration_ms)
        titles[tc.id] = tc.title or f"Case #{tc.id}"
    slow: List[SlowTest] = []
    for cid, durs in by_case.items():
        slow.append(
            SlowTest(
                test_case_id=cid,
                title=titles[cid],
                p95_ms=_p95(durs),
                runs_used=len(durs),
            )
        )
    slow.sort(key=lambda x: (-x.p95_ms, x.title.lower()))
    return slow[:top]


def stale_tests(
    ready_cases: List[TestCase],
    case_ids_in_window: set[int],
) -> List[StaleTest]:
    stale: List[StaleTest] = []
    for tc in ready_cases:
        if tc.id not in case_ids_in_window:
            stale.append(
                StaleTest(
                    test_case_id=tc.id,
                    title=tc.title or f"Case #{tc.id}",
                    last_executed_at=None,
                )
            )
    stale.sort(key=lambda x: x.title.lower())
    return stale
