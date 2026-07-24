"""Lane watchdog policy: slow-case + stale-heartbeat reassignment."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import settings


@dataclass
class CaseWatch:
    test_case_id: int
    lane_id: int
    started_at: float
    last_heartbeat_at: float
    reassign_count: int = 0
    title: str = ""


@dataclass
class WatchdogDecision:
    action: str  # "ok" | "reassign" | "quarantine_lane"
    reason: str = ""
    test_case_id: Optional[int] = None
    lane_id: Optional[int] = None


@dataclass
class LaneHealth:
    infra_failures: int = 0
    quarantined: bool = False


class LaneWatchdog:
    """Tracks per-case heartbeats and decides when to cancel+reassign."""

    def __init__(self) -> None:
        self._active: Dict[int, CaseWatch] = {}  # test_case_id -> watch
        self._lane_health: Dict[int, LaneHealth] = {}
        self.reassign_events: List[Dict[str, Any]] = []

    @property
    def slow_case_ms(self) -> int:
        return int(getattr(settings, "SLOW_CASE_MS", 480_000) or 480_000)

    @property
    def heartbeat_s(self) -> float:
        return float(getattr(settings, "LANE_HEARTBEAT_S", 30.0) or 30.0)

    @property
    def max_reassigns(self) -> int:
        return int(getattr(settings, "MAX_CASE_REASSIGNS", 2) or 2)

    @property
    def quarantine_failures(self) -> int:
        return int(getattr(settings, "LANE_QUARANTINE_FAILURES", 3) or 3)

    def start_case(
        self,
        *,
        test_case_id: int,
        lane_id: int,
        reassign_count: int = 0,
        title: str = "",
    ) -> None:
        now = time.monotonic()
        self._active[test_case_id] = CaseWatch(
            test_case_id=test_case_id,
            lane_id=lane_id,
            started_at=now,
            last_heartbeat_at=now,
            reassign_count=reassign_count,
            title=title,
        )

    def heartbeat(self, test_case_id: int) -> None:
        w = self._active.get(test_case_id)
        if w:
            w.last_heartbeat_at = time.monotonic()

    def finish_case(self, test_case_id: int) -> Optional[CaseWatch]:
        return self._active.pop(test_case_id, None)

    def evaluate(self, test_case_id: int, *, now: Optional[float] = None) -> WatchdogDecision:
        w = self._active.get(test_case_id)
        if not w:
            return WatchdogDecision(action="ok")
        t = now if now is not None else time.monotonic()
        elapsed_ms = (t - w.started_at) * 1000.0
        elapsed_s = elapsed_ms / 1000.0
        stale_s = t - w.last_heartbeat_at
        min_before_stale = float(
            getattr(settings, "WATCHDOG_MIN_ELAPSED_BEFORE_STALE_S", 90.0) or 90.0
        )
        if elapsed_ms > self.slow_case_ms:
            return WatchdogDecision(
                action="reassign",
                reason=f"slow_case elapsed_ms={int(elapsed_ms)}",
                test_case_id=test_case_id,
                lane_id=w.lane_id,
            )
        # Don't stale-reassign early — vision LLM steps can be quiet for a while.
        if elapsed_s >= min_before_stale and stale_s > self.heartbeat_s:
            return WatchdogDecision(
                action="reassign",
                reason=f"stale_heartbeat {stale_s:.1f}s",
                test_case_id=test_case_id,
                lane_id=w.lane_id,
            )
        return WatchdogDecision(action="ok")

    def can_reassign(self, test_case_id: int) -> bool:
        w = self._active.get(test_case_id)
        count = w.reassign_count if w else 0
        return count < self.max_reassigns

    def record_reassign(self, *, test_case_id: int, reason: str, from_lane: int) -> int:
        w = self._active.get(test_case_id)
        new_count = (w.reassign_count if w else 0) + 1
        self.reassign_events.append(
            {
                "test_case_id": test_case_id,
                "from_lane": from_lane,
                "reason": reason,
                "reassign_count": new_count,
            }
        )
        self.finish_case(test_case_id)
        return new_count

    def record_infra_failure(self, lane_id: int) -> WatchdogDecision:
        health = self._lane_health.setdefault(lane_id, LaneHealth())
        health.infra_failures += 1
        if health.infra_failures >= self.quarantine_failures:
            health.quarantined = True
            return WatchdogDecision(
                action="quarantine_lane",
                reason=f"infra_failures={health.infra_failures}",
                lane_id=lane_id,
            )
        return WatchdogDecision(action="ok", lane_id=lane_id)

    def clear_quarantine(self, lane_id: int) -> None:
        health = self._lane_health.setdefault(lane_id, LaneHealth())
        health.quarantined = False
        health.infra_failures = 0

    def is_quarantined(self, lane_id: int) -> bool:
        return bool(self._lane_health.get(lane_id) and self._lane_health[lane_id].quarantined)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "reassign_events": list(self.reassign_events),
            "active": {
                str(k): {
                    "lane_id": v.lane_id,
                    "reassign_count": v.reassign_count,
                    "elapsed_ms": int((time.monotonic() - v.started_at) * 1000),
                }
                for k, v in self._active.items()
            },
            "lanes": {
                str(k): {
                    "infra_failures": v.infra_failures,
                    "quarantined": v.quarantined,
                }
                for k, v in self._lane_health.items()
            },
        }
