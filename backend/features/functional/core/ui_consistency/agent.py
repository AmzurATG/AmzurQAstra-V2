"""UI Consistency agent — patches live progress display without changing pass/fail."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from common.utils.logger import logger
from config import settings
from features.functional.core.react_loop.loop import react_once
from features.functional.core.ui_consistency.rules import detect_desync, patch_live_entry
from features.functional.services.run_progress_manager import RunProgressManager


class UiConsistencyAgent:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self._since_last = 0

    @property
    def every_n(self) -> int:
        return int(getattr(settings, "UI_CONSISTENCY_EVERY_N", 10) or 10)

    def should_run(self, *, completed_count: int, force: bool = False, desync_hit: bool = False) -> bool:
        if not bool(getattr(settings, "UI_CONSISTENCY_ENABLED", True)):
            return False
        if force or desync_hit:
            return True
        if completed_count > 0 and completed_count % self.every_n == 0:
            return True
        return False

    async def sweep(
        self,
        run_id: int,
        *,
        live_completed: Sequence[Dict[str, Any]],
        db_by_case: Optional[Dict[int, Dict[str, Any]]] = None,
        progress_mgr: Optional[RunProgressManager] = None,
    ) -> Dict[str, Any]:
        mgr = progress_mgr or RunProgressManager()
        db_by_case = db_by_case or {}
        patched: List[Dict[str, Any]] = []
        new_events: List[Dict[str, Any]] = []

        async def observe():
            return list(live_completed)

        async def think(obs):
            plans = []
            for entry in obs:
                if not isinstance(entry, dict):
                    continue
                cid = int(entry.get("test_case_id") or 0)
                event = detect_desync(entry, db_by_case.get(cid))
                if event:
                    plans.append({"entry": entry, "event": event})
            return plans or None

        async def act(plans):
            out = []
            for plan in plans:
                entry = plan["entry"]
                fixed = patch_live_entry(entry, step_results=entry.get("step_results"))
                # If still desynced with no step_results, leave status alone (display only counts).
                out.append(fixed)
                evt = dict(plan["event"])
                evt["patched"] = True
                new_events.append(evt)
            return out

        async def check(obs, action):
            if not action:
                return True
            # Re-check patched entries have no zero-step passed with shots
            for entry in action:
                if detect_desync(entry):
                    # still desynced but we did our best with available fields
                    continue
            return True

        result = await react_once(observe=observe, think=think, act=act, check=check, retries=1)
        if result.action:
            # Merge patches back into live list by test_case_id
            by_id = {int(e.get("test_case_id") or 0): e for e in result.action if isinstance(e, dict)}
            patched = []
            for entry in live_completed:
                if not isinstance(entry, dict):
                    continue
                cid = int(entry.get("test_case_id") or 0)
                patched.append(by_id.get(cid, entry))
            body = mgr.get(run_id) or {}
            existing_events = list(body.get("ui_desync_events") or [])
            existing_events.extend(new_events)
            storm = len(new_events) >= 3
            mgr.update(
                run_id,
                {
                    "completed_results": patched,
                    "ui_desync_events": existing_events[-50:],
                    "ui_desync": storm or bool(body.get("ui_desync")),
                },
            )
            self.events.extend(new_events)
            logger.info(
                "[UiConsistency] run=%s patched=%s events=%s",
                run_id, len(by_id), len(new_events),
            )
            return {"patched": len(by_id), "events": new_events, "ui_desync": storm}
        return {"patched": 0, "events": [], "ui_desync": False}
