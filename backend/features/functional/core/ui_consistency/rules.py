"""Rule-based live vs DB desync detection (display truth only)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def detect_desync(
    live: Dict[str, Any],
    db: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Return a desync event dict if live display looks wrong; else None."""
    status = str(live.get("status") or "").lower()
    steps_passed = int(live.get("steps_passed") or 0)
    steps_total = int(live.get("steps_total") or 0)
    shots = int(live.get("agent_screenshot_count") or 0)
    if live.get("screenshot_path"):
        shots = max(shots, 1)
    setup_skipped = live.get("setup_skipped_count")
    reasons: List[str] = []

    if status == "passed" and steps_passed == 0 and shots > 0 and steps_total > 0:
        reasons.append("passed_with_zero_verified_steps")
    if status == "passed" and steps_total == 0 and shots > 0:
        reasons.append("passed_with_zero_total_steps")
    if setup_skipped is None and live.get("step_results"):
        # lite payloads may omit; only flag when full payload lacks field after builder
        pass
    if db:
        db_status = str(db.get("status") or "").lower()
        if db_status and status and db_status != status:
            reasons.append(f"status_mismatch_live={status}_db={db_status}")
        for key in ("steps_passed", "steps_total", "setup_skipped_count"):
            if key in db and key in live and db.get(key) != live.get(key):
                reasons.append(f"{key}_mismatch")

    if not reasons:
        return None
    return {
        "test_case_id": live.get("test_case_id"),
        "test_result_id": live.get("test_result_id"),
        "reasons": reasons,
        "live_status": status,
        "live_steps_passed": steps_passed,
        "live_steps_total": steps_total,
    }


def corrected_counts_from_steps(step_results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    from features.functional.core.grouping.setup_step_merger import compute_step_display_counts

    return compute_step_display_counts(list(step_results or []))


def patch_live_entry(live: Dict[str, Any], *, step_results: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Return a corrected copy of a live completed_results entry."""
    out = dict(live)
    steps = list(step_results if step_results is not None else (live.get("step_results") or []))
    if steps:
        counts = corrected_counts_from_steps(steps)
        out["steps_total"] = counts["steps_total"]
        out["steps_passed"] = counts["steps_passed"]
        out["steps_failed"] = counts["steps_failed"]
        out["setup_skipped_count"] = counts["setup_skipped_count"]
        out["step_results"] = steps
    return out
