"""Vision-retry node: re-run failed cases with stronger vision model."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import config
from features.functional.core.browser.test_case_runner import TestCaseRunner
from features.functional.orchestration.lane_pool import LanePool
from features.functional.orchestration.nodes.executor import _run_single_case
from features.functional.orchestration.state import CaseResult, OrchestrationState
from features.functional.services.run_progress_manager import RunProgressManager
from common.utils.logger import logger


async def vision_retry_node(state: OrchestrationState) -> Dict[str, Any]:
    failed_ids = set(int(x) for x in (state.get("failed_case_ids") or []))
    if not failed_ids:
        return {"retry_results": [], "status": "reporting"}

    run_id = int(state["run_id"])
    progress_mgr = RunProgressManager()
    if progress_mgr.is_cancel_requested(run_id):
        return {"status": "cancelled", "cancel_requested": True}

    # If the shared LLM circuit is open (proxy down / budget gone), skip the
    # (expensive) retry pass entirely — retrying now would just burn budget and
    # produce empty errors. The main verdicts stand; resume can re-verify later.
    from features.functional.core.browser.llm_gate import get_gate

    if get_gate().should_pause():
        logger.warning(
            "[VisionRetry] Skipping retry for run %s — LLM circuit open/budget gone.",
            run_id,
        )
        return {"retry_results": [], "status": "reporting"}

    case_map = {int(c["test_case_id"]): c for c in (state.get("cases") or [])}
    run_uuid = state.get("run_uuid") or str(uuid.uuid4())
    headless = bool(state.get("headless"))

    # Retry model: explicit config if set (must be provisioned + funded on the
    # proxy), otherwise reuse the main model. Passed per-case so we never mutate
    # the global env (racy across lanes). Empty → main model (avoids the run #14
    # failure where a separate gpt-4o model was over-budget and every retry died).
    retry_model = (
        getattr(config.settings, "ORCHESTRATION_VISION_RETRY_MODEL", "") or ""
    ).strip() or None

    pool = LanePool(headless=headless, lane_count=1)
    await pool.start()
    lane = await pool.acquire()
    runner = TestCaseRunner()
    retry_results: List[CaseResult] = []

    try:
        for cid in failed_ids:
            if progress_mgr.is_cancel_requested(run_id):
                break
            case = case_map.get(cid)
            if not case:
                continue
            logger.info(
                "[VisionRetry] Re-running case %s with model %s",
                cid, retry_model or "(main model)",
            )
            try:
                cr = await _run_single_case(
                    runner=runner,
                    run_uuid=run_uuid,
                    run_id=run_id,
                    case=case,
                    lane_id=lane.lane_id,
                    group_id=f"retry_{cid}",
                    browser=lane.browser,
                    app_url=state.get("app_url") or "",
                    username=state.get("username"),
                    password=state.get("password"),
                    use_google_signin=bool(state.get("use_google_signin")),
                    headless=headless,
                    progress_mgr=progress_mgr,
                    on_step=None,
                    llm_model=retry_model,
                )
                cr["status"] = cr.get("status") or "failed"
                retry_results.append(cr)
            except Exception as exc:
                retry_results.append(
                    CaseResult(
                        test_case_id=cid,
                        test_result_id=int(case.get("test_result_id") or 0),
                        title=str(case.get("title") or ""),
                        status="error",
                        duration_ms=0,
                        step_results=[],
                        adapted_steps=[],
                        original_steps=list(case.get("steps") or []),
                        agent_logs=[],
                        screenshot_path=None,
                        ai_modified={"steps": {}, "has_changes": False},
                        error=str(exc),
                        group_id=f"retry_{cid}",
                        lane_id=lane.lane_id,
                    )
                )
    finally:
        await pool.release(lane, recycle=True)
        await pool.shutdown()

    still_failed = [
        int(r["test_case_id"])
        for r in retry_results
        if r.get("status") not in ("passed", "cancelled", "skipped")
    ]
    return {
        "retry_results": retry_results,
        "failed_case_ids": still_failed,
        "status": "reporting",
    }
