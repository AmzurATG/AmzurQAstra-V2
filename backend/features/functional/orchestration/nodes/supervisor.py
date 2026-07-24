"""Supervisor node: preflight checks + lane contract before planning."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from common.utils.logger import logger
from config import settings
from features.functional.core.memory.store import format_memory_prompt_hint, load_memory
from features.functional.core.supervisor.preflight import (
    build_supervisor_state,
    check_screenshot_dir,
    expected_lane_count,
)
from features.functional.orchestration.state import OrchestrationState
from features.functional.services.run_progress_manager import RunProgressManager


async def supervisor_node(state: OrchestrationState) -> Dict[str, Any]:
    if not bool(getattr(settings, "SUPERVISOR_ENABLED", True)):
        lanes = expected_lane_count(state.get("lane_count"))
        return {
            "lane_count": lanes,
            "supervisor": build_supervisor_state(
                lanes_expected=lanes, lanes_ready=lanes
            ),
            "status": "planning",
        }

    run_id = int(state["run_id"])
    progress_mgr = RunProgressManager()
    health_events: list = []
    lanes_expected = expected_lane_count(
        state.get("lane_count")
        or getattr(settings, "ORCHESTRATION_LANE_COUNT", 6)
    )

    shot_err = check_screenshot_dir()
    if shot_err:
        health_events.append({"type": "screenshot_dir", "ok": False, "detail": shot_err})
    else:
        health_events.append({"type": "screenshot_dir", "ok": True})

    # DB connectivity probe via existing session maker
    db_ok = True
    try:
        from sqlalchemy import text
        from common.db.database import async_session_maker

        async with async_session_maker() as db:
            await db.execute(text("SELECT 1"))
        health_events.append({"type": "db", "ok": True})
    except Exception as exc:
        db_ok = False
        health_events.append({"type": "db", "ok": False, "detail": str(exc)[:200]})

    # Lane contract: we assert the *effective* count we will request.
    # Actual browser start happens in execute; here we validate config math.
    lanes_ready = lanes_expected
    if lanes_expected < 1:
        lanes_ready = 0
        health_events.append({"type": "lanes", "ok": False, "detail": "lane_count < 1"})
    else:
        health_events.append(
            {
                "type": "lanes",
                "ok": True,
                "lanes_expected": lanes_expected,
                "note": "Browsers start at execute; count is RAM-aware scale-down only.",
            }
        )

    abort = False
    abort_reason = None
    if not db_ok:
        abort = True
        abort_reason = "Database unavailable during supervisor preflight"
    if shot_err:
        abort = True
        abort_reason = shot_err
    if lanes_ready < 1:
        abort = True
        abort_reason = "Cannot start run: no browser lanes available"

    supervisor = build_supervisor_state(
        lanes_expected=lanes_expected,
        lanes_ready=lanes_ready,
        health_events=health_events,
        abort=abort,
        abort_reason=abort_reason,
    )

    project_id = int(state.get("project_id") or 0)
    memory_hint = format_memory_prompt_hint(project_id) if project_id else ""
    mem = load_memory(project_id) if project_id else {}

    if abort:
        logger.error("[Supervisor] Aborting run %s: %s", run_id, abort_reason)
        progress_mgr.update(
            run_id,
            {
                "status": "error",
                "error": abort_reason,
                "current_step_info": abort_reason,
                "supervisor": supervisor,
            },
        )
        return {
            "status": "error",
            "error": abort_reason,
            "lane_count": lanes_expected,
            "supervisor": supervisor,
            "memory_hints": mem.get("hints") or [],
            "cancel_requested": False,
        }

    progress_mgr.update(
        run_id,
        {
            "status": "supervising",
            "current_step_info": f"Supervisor OK — {lanes_expected} lanes expected",
            "supervisor": supervisor,
        },
    )
    logger.info(
        "[Supervisor] run=%s lanes_expected=%s memory_hints=%s",
        run_id, lanes_expected, len(mem.get("hints") or []),
    )
    return {
        "lane_count": lanes_expected,
        "supervisor": supervisor,
        "memory_hints": mem.get("hints") or [],
        "recon_prompt_hint": memory_hint,  # soft hints; recon node may append
        "status": "recon" if bool(getattr(settings, "RECON_ENABLED", True)) else "planning",
    }
