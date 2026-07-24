"""Local browser lane pool: 2 Chrome processes x 3 contexts (6 lanes)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from browser_use import Browser, BrowserProfile

import config
from common.utils.logger import logger
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args


def _free_ram_mb() -> Optional[float]:
    try:
        import psutil

        return psutil.virtual_memory().available / (1024 * 1024)
    except Exception:
        return None


def effective_lane_count(requested: int) -> int:
    """RAM-aware lane count that honors the requested baseline.

    - Baseline = min(requested, ORCHESTRATION_MAX_LANE_COUNT).
    - Optional ACCURACY_LANE_COUNT_CAP (>0) further caps the baseline.
    - Scales DOWN when free RAM cannot support the baseline.
    - Scales UP only when ORCHESTRATION_LANE_SCALE_UP is True (off by default).
    """
    configured = max(1, int(getattr(config.settings, "ORCHESTRATION_LANE_COUNT", 6) or 6))
    hard_max = max(configured, int(getattr(config.settings, "ORCHESTRATION_MAX_LANE_COUNT", 12) or 12))
    baseline = max(1, min(int(requested or configured), hard_max))
    cap = int(getattr(config.settings, "ACCURACY_LANE_COUNT_CAP", 0) or 0)
    if cap > 0:
        baseline = max(1, min(baseline, cap))
    free = _free_ram_mb()
    min_free = float(getattr(config.settings, "ORCHESTRATION_MIN_FREE_RAM_MB", 1200) or 1200)
    per_lane = float(getattr(config.settings, "ORCHESTRATION_PER_LANE_RAM_MB", 450) or 450)
    if free is None:
        return baseline
    max_by_ram = max(1, int((free - min_free) / per_lane))
    if max_by_ram < baseline:
        logger.warning(
            "[LanePool] RAM guard reduced lanes %s -> %s (free=%.0fMB)",
            baseline, max_by_ram, free,
        )
        return max_by_ram
    scale_up = bool(getattr(config.settings, "ORCHESTRATION_LANE_SCALE_UP", False))
    if scale_up and max_by_ram > baseline:
        bumped = min(hard_max, max_by_ram)
        if bumped > baseline:
            logger.info(
                "[LanePool] RAM headroom allows scaling lanes %s -> %s (free=%.0fMB)",
                baseline, bumped, free,
            )
        return bumped
    return baseline


@dataclass
class LaneHandle:
    lane_id: int
    chrome_group: int
    browser: Browser
    cases_executed: int = 0
    busy: bool = False
    current_group_id: Optional[str] = None
    last_heartbeat_at: Optional[float] = None
    case_started_at: Optional[float] = None
    current_case_id: Optional[int] = None
    reassign_count: int = 0
    quarantined: bool = False


class LanePool:
    """Manages N local Chrome browsers grouped for periodic process recycle."""

    def __init__(
        self,
        *,
        headless: bool = False,
        lane_count: Optional[int] = None,
    ) -> None:
        self.headless = headless
        self._requested = lane_count or int(
            getattr(config.settings, "ORCHESTRATION_LANE_COUNT", 6) or 6
        )
        self.lane_count = effective_lane_count(self._requested)
        self._chrome_processes = int(
            getattr(config.settings, "ORCHESTRATION_CHROME_PROCESSES", 2) or 2
        )
        self._contexts_per_chrome = int(
            getattr(config.settings, "ORCHESTRATION_CONTEXTS_PER_CHROME", 3) or 3
        )
        self._lanes: Dict[int, LaneHandle] = {}
        self._lock = asyncio.Lock()
        self._recycle_after = 50

    def _build_browser(self) -> Browser:
        return Browser(
            browser_profile=BrowserProfile(
                headless=self.headless,
                is_local=True,
                disable_security=True,
                args=default_browser_chrome_args(),
                enable_default_extensions=config.settings.BROWSER_USE_DEFAULT_EXTENSIONS,
                keep_alive=True,
            )
        )

    async def start(self) -> None:
        async with self._lock:
            for i in range(1, self.lane_count + 1):
                chrome_group = (i - 1) // self._contexts_per_chrome + 1
                browser = self._build_browser()
                self._lanes[i] = LaneHandle(
                    lane_id=i,
                    chrome_group=chrome_group,
                    browser=browser,
                )
                logger.info("[LanePool] Lane %s online (chrome group %s)", i, chrome_group)

    async def acquire(self) -> LaneHandle:
        while True:
            async with self._lock:
                for lane in self._lanes.values():
                    if not lane.busy:
                        lane.busy = True
                        return lane
            await asyncio.sleep(0.2)

    async def release(self, lane: LaneHandle, *, recycle: bool = False) -> None:
        async with self._lock:
            lane.busy = False
            lane.current_group_id = None
            lane.cases_executed += 1
            if recycle or lane.cases_executed >= self._recycle_after:
                await self._recycle_lane(lane)

    async def _recycle_lane(self, lane: LaneHandle) -> None:
        try:
            await lane.browser.kill()
        except Exception as exc:
            logger.warning("[LanePool] Lane %s kill failed: %s", lane.lane_id, exc)
        lane.browser = self._build_browser()
        lane.cases_executed = 0
        logger.info("[LanePool] Lane %s browser recycled", lane.lane_id)

    async def recycle_chrome_group(self, chrome_group: int) -> None:
        async with self._lock:
            for lane in self._lanes.values():
                if lane.chrome_group == chrome_group and not lane.busy:
                    await self._recycle_lane(lane)

    def lane_snapshot(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for lane in self._lanes.values():
            out.append(
                {
                    "worker_id": lane.lane_id,
                    "lane_id": lane.lane_id,
                    "chrome_group": lane.chrome_group,
                    "busy": lane.busy,
                    "group_id": lane.current_group_id,
                    "title": lane.current_group_id or ("Idle" if not lane.busy else "…"),
                    "step": "Running" if lane.busy else "Idle",
                }
            )
        return out

    async def shutdown(self) -> None:
        async with self._lock:
            for lane in self._lanes.values():
                try:
                    await lane.browser.kill()
                except Exception:
                    pass
            self._lanes.clear()
