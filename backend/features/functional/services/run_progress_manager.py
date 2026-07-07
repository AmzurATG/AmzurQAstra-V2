"""
Run Progress Manager - encapsulates in-memory test run progress.

Module-level dicts guarantee cross-thread visibility: they live in the
module's __dict__ (a single object, shared across all threads in the
process) rather than as class attributes that could theoretically be
shadowed by instance variables or a second class object produced by a
hot-reload cycle that hasn't yet replaced the background thread's stale
class reference.
"""
import threading
from typing import Any, Dict, Optional, List
from common.utils.logger import logger

# Module-level storage — guaranteed to be the same object in every thread.
_PROGRESS: Dict[int, Dict[str, Any]] = {}
_CANCEL_EVENTS: Dict[int, threading.Event] = {}
_CANCEL_LOCK = threading.Lock()


class RunProgressManager:
    """Manages in-memory progress for active test runs."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RunProgressManager, cls).__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------
    # All methods delegate to the module-level dicts so they are visible
    # from every thread in the process regardless of which class object
    # the caller has (hot-reload can produce a new class object; the
    # module-level dicts remain the same).
    # ------------------------------------------------------------------

    def get(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get progress for a run."""
        return _PROGRESS.get(run_id)

    def set(self, run_id: int, data: Dict[str, Any]) -> None:
        """Set (replace) progress for a run."""
        logger.debug(f"[RunProgressManager] set run_id={run_id} keys={list(data.keys())}")
        _PROGRESS[run_id] = data

    def update(self, run_id: int, updates: Dict[str, Any]) -> None:
        """Merge updates into existing progress without clobbering other keys."""
        if run_id in _PROGRESS:
            _PROGRESS[run_id].update(updates)
        else:
            _PROGRESS[run_id] = dict(updates)

    def add_log(self, run_id: int, log_entry: Dict[str, Any]) -> None:
        """Append a single log entry; creates the progress slot if absent."""
        if run_id not in _PROGRESS:
            _PROGRESS[run_id] = {"logs": []}
        if "logs" not in _PROGRESS[run_id]:
            _PROGRESS[run_id]["logs"] = []
        _PROGRESS[run_id]["logs"].append(log_entry)

    def cleanup(self, run_id: int) -> None:
        """Remove all progress state for a completed run."""
        _PROGRESS.pop(run_id, None)
        self.clear_cancel(run_id)

    def request_cancel(self, run_id: int) -> None:
        """Signal background execution to stop (cross-thread safe)."""
        with _CANCEL_LOCK:
            ev = _CANCEL_EVENTS.setdefault(run_id, threading.Event())
            ev.set()

    def is_cancel_requested(self, run_id: int) -> bool:
        with _CANCEL_LOCK:
            ev = _CANCEL_EVENTS.get(run_id)
            return bool(ev and ev.is_set())

    def clear_cancel(self, run_id: int) -> None:
        with _CANCEL_LOCK:
            _CANCEL_EVENTS.pop(run_id, None)

    def schedule_cleanup(self, run_id: int, delay_seconds: int = 300) -> None:
        """Schedule progress cleanup after a delay using a daemon timer thread."""
        def _delayed_cleanup() -> None:
            self.cleanup(run_id)
            logger.info(f"[RunProgressManager] Cleaned up progress for run_id={run_id}")

        t = threading.Timer(delay_seconds, _delayed_cleanup)
        t.daemon = True
        t.start()
