"""Supervisor preflight and health helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings


def expected_lane_count(requested: Optional[int] = None) -> int:
    # Lazy import avoids circular import via orchestration package __init__.
    from features.functional.orchestration.lane_pool import effective_lane_count

    configured = int(getattr(settings, "ORCHESTRATION_LANE_COUNT", 6) or 6)
    req = int(requested or configured)
    cap = int(getattr(settings, "ACCURACY_LANE_COUNT_CAP", 0) or 0)
    if cap > 0:
        req = min(req, cap)
    return effective_lane_count(req)


def check_screenshot_dir() -> Optional[str]:
    root = Path(getattr(settings, "SCREENSHOTS_DIR", "") or "")
    if not root:
        return "SCREENSHOTS_DIR is not configured"
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".supervisor_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        return f"Screenshot directory not writable: {exc}"
    return None


def build_supervisor_state(
    *,
    lanes_expected: int,
    lanes_ready: int,
    health_events: Optional[List[Dict[str, Any]]] = None,
    abort: bool = False,
    abort_reason: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "lanes_expected": lanes_expected,
        "lanes_ready": lanes_ready,
        "health_events": list(health_events or []),
        "abort": abort,
        "abort_reason": abort_reason,
    }
