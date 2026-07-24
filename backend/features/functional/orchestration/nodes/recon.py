"""Recon node: one-shot login/DOM scout before planning."""
from __future__ import annotations

from typing import Any, Dict

from common.utils.logger import logger
from config import settings
from features.functional.core.memory.store import append_event
from features.functional.core.recon.scout import format_recon_prompt_hint, run_recon_scout
from features.functional.orchestration.state import OrchestrationState
from features.functional.services.run_progress_manager import RunProgressManager


async def recon_node(state: OrchestrationState) -> Dict[str, Any]:
    if not bool(getattr(settings, "RECON_ENABLED", True)):
        return {"status": "planning", "recon_cache": None}

    # Supervisor abort short-circuit
    supervisor = state.get("supervisor") or {}
    if supervisor.get("abort"):
        return {"status": "error", "error": supervisor.get("abort_reason")}

    run_id = int(state["run_id"])
    progress_mgr = RunProgressManager()
    progress_mgr.update(
        run_id,
        {
            "status": "recon",
            "current_step_info": "Recon scout: mapping app shell…",
        },
    )

    cache = await run_recon_scout(
        app_url=str(state.get("app_url") or ""),
        username=state.get("username"),
        password=state.get("password"),
        use_google_signin=bool(state.get("use_google_signin")),
        headless=bool(state.get("headless", True)),
    )

    project_id = int(state.get("project_id") or 0)
    if not cache.get("ok") and project_id:
        append_event(
            project_id,
            {"type": "recon_failure", "error": cache.get("error"), "run_id": run_id},
            hint="Prior recon failed — verify app_url and login selectors before trusting DOM hints.",
        )

    if cache.get("auth_broken"):
        msg = "Recon: authentication appears completely broken — aborting run"
        logger.error("[Recon] %s", msg)
        progress_mgr.update(run_id, {"status": "error", "error": msg, "current_step_info": msg})
        return {
            "status": "error",
            "error": msg,
            "recon_cache": cache,
        }

    hint = format_recon_prompt_hint(cache)
    prior = str(state.get("recon_prompt_hint") or "")
    combined = "\n\n".join(x for x in (prior, hint) if x)

    logger.info(
        "[Recon] run=%s ok=%s outline=%s",
        run_id, cache.get("ok"), len(cache.get("dom_outline") or []),
    )
    progress_mgr.update(
        run_id,
        {
            "current_step_info": "Recon complete — planning groups…",
            "recon_ok": bool(cache.get("ok")),
        },
    )
    return {
        "recon_cache": cache,
        "recon_prompt_hint": combined,
        "status": "planning",
    }
