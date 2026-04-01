"""
Run Progress Manager - encapsulates in-memory test run progress.
"""
import threading
from typing import Any, Dict, Optional, List
from common.utils.logger import logger

class RunProgressManager:
    """Manages in-memory progress for active test runs."""
    
    _instance = None
    _progress: Dict[int, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RunProgressManager, cls).__new__(cls)
        return cls._instance
    
    def get(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get progress for a run."""
        return self._progress.get(run_id)
    
    def set(self, run_id: int, data: Dict[str, Any]) -> None:
        """Set progress for a run."""
        self._progress[run_id] = data
        
    def update(self, run_id: int, updates: Dict[str, Any]) -> None:
        """Update existing progress for a run."""
        if run_id in self._progress:
            self._progress[run_id].update(updates)
        else:
            self._progress[run_id] = updates
            
    def add_log(self, run_id: int, log_entry: Dict[str, Any]) -> None:
        """Add a log entry to a run's progress."""
        if run_id not in self._progress:
            self._progress[run_id] = {"logs": []}
        
        if "logs" not in self._progress[run_id]:
            self._progress[run_id]["logs"] = []
            
        self._progress[run_id]["logs"].append(log_entry)
        
    def cleanup(self, run_id: int) -> None:
        """Remove progress for a run."""
        self._progress.pop(run_id, None)
        
    def schedule_cleanup(self, run_id: int, delay_seconds: int = 300) -> None:
        """
        Schedule progress cleanup after a delay.

        Uses a daemon thread timer so cleanup still runs when execution used a
        temporary event loop (e.g. Windows Proactor thread) that is closed afterward.
        """
        def _delayed_cleanup() -> None:
            self.cleanup(run_id)
            logger.info(f"[RunProgressManager] Cleaned up progress for run_id={run_id}")

        t = threading.Timer(delay_seconds, _delayed_cleanup)
        t.daemon = True
        t.start()
