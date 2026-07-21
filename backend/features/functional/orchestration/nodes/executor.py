"""Execute node: dispatch groups across lane pool with phase ordering."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from features.functional.core.browser.test_case_runner import TestCaseRunner
from features.functional.core.browser.llm_gate import get_gate
from features.functional.orchestration.lane_pool import LanePool
from features.functional.orchestration.result_persistence import (
    case_result_to_completed_dict,
    persist_single_result,
)
from features.functional.orchestration.state import CaseResult, GroupRow, OrchestrationState
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.utils.credentials_redaction import (
    redact_agent_logs_list,
    redact_known_credentials,
    redact_step_dict,
)
from common.utils.logger import logger


def _cases_by_id(state: OrchestrationState) -> Dict[int, Dict[str, Any]]:
    return {int(c["test_case_id"]): c for c in (state.get("cases") or [])}


def _phase_sort_key(group: GroupRow, case_id: int) -> int:
    phases = group.get("phase_order") or ["authed"]
    case_phases = group.get("case_phases") or {}
    ph = case_phases.get(str(case_id), "authed")
    try:
        return phases.index(ph)
    except ValueError:
        return len(phases)


async def _run_single_case(
    *,
    runner: TestCaseRunner,
    run_uuid: str,
    run_id: int,
    case: Dict[str, Any],
    lane_id: int,
    group_id: str,
    browser: Any,
    app_url: str,
    username: Optional[str],
    password: Optional[str],
    use_google_signin: bool,
    headless: bool,
    progress_mgr: RunProgressManager,
    on_step,
    llm_model: Optional[str] = None,
) -> CaseResult:
    tc_id = int(case["test_case_id"])
    result = await runner.run(
        run_id=run_uuid,
        test_case_id=tc_id,
        title=str(case.get("title") or ""),
        description=str(case.get("description") or ""),
        preconditions=str(case.get("preconditions") or ""),
        steps=list(case.get("steps") or []),
        app_url=app_url,
        username=username,
        password=password,
        use_google_signin=use_google_signin,
        headless=headless,
        capture_screenshots=True,
        browser_context=browser,
        on_step_callback=on_step,
        execution_run_id=run_id,
        llm_model=llm_model,
    )
    tc_status = result.get("overall", "error")
    llm_steps = {s.get("step_number"): s for s in result.get("step_results", [])}
    final_steps: List[Dict[str, Any]] = []
    ai_modified: Dict[str, Any] = {"steps": {}, "has_changes": False}
    for s_orig in case.get("steps") or []:
        num = s_orig.get("step_number")
        s_res = llm_steps.get(num, {})
        merged = {
            **s_orig,
            "status": s_res.get("status", "skipped"),
            "actual_result": s_res.get("actual_result"),
            "adaptation": s_res.get("adaptation"),
        }
        redacted = redact_step_dict(merged, username, password)
        final_steps.append(redacted)
        if redacted.get("adaptation"):
            ai_modified["has_changes"] = True
            ai_modified["steps"][str(num)] = redacted.get("adaptation")

    safe_logs = redact_agent_logs_list(result.get("logs"), username, password) or []
    shots = list(result.get("screenshots") or [])
    return CaseResult(
        test_case_id=tc_id,
        test_result_id=int(case.get("test_result_id") or 0),
        title=str(case.get("title") or ""),
        status=tc_status,
        duration_ms=int(result.get("duration_ms") or 0),
        step_results=final_steps,
        adapted_steps=[s for s in final_steps if s.get("adaptation")],
        original_steps=list(case.get("steps") or []),
        agent_logs=safe_logs,
        screenshot_path=(shots[-1] if shots else None),
        ai_modified=ai_modified,
        error=redact_known_credentials(
            result.get("error"), username=username, password=password
        ),
        error_kind=result.get("error_kind"),
        infra_error=bool(result.get("infra_error")),
        group_id=group_id,
        lane_id=lane_id,
    )


async def _execute_group_on_lane(
    group: GroupRow,
    lane,
    pool: LanePool,
    state: OrchestrationState,
    runner: TestCaseRunner,
    run_uuid: str,
    progress_mgr: RunProgressManager,
    results_out: List[CaseResult],
    results_lock: asyncio.Lock,
    live_completed: List[Dict[str, Any]],
    live_shots: List[str],
) -> None:
    run_id = int(state["run_id"])
    case_map = _cases_by_id(state)
    app_url = state.get("app_url") or ""
    username = state.get("username")
    password = state.get("password")
    use_google_signin = bool(state.get("use_google_signin"))
    headless = bool(state.get("headless"))
    group_id = str(group.get("group_id") or "G")
    lane.current_group_id = group_id
    case_ids = sorted(
        [int(x) for x in (group.get("case_ids") or [])],
        key=lambda cid: _phase_sort_key(group, cid),
    )

    async def _on_step(step_num, desc, log_entry, *, _cid=None, _title=""):
        shot = log_entry.get("screenshot_path") if log_entry else None
        lanes = pool.lane_snapshot()
        for ln in lanes:
            if ln["lane_id"] == lane.lane_id:
                ln["title"] = _title or group_id
                ln["step"] = desc
                ln["test_case_id"] = _cid
                ln["step_num"] = step_num
        progress_mgr.update(
            run_id,
            {
                "active_lanes": lanes,
                "current_step_info": f"Lane {lane.lane_id}: {desc}",
            },
        )

    recycle_after_group = bool(group.get("shared_login"))
    for cid in case_ids:
        if progress_mgr.is_cancel_requested(run_id):
            break
        case = case_map.get(cid)
        if not case:
            continue
        tc_title = str(case.get("title") or f"Case {cid}")

        async def _cb(step_num, desc, log_entry, _cid=cid, _title=tc_title):
            await _on_step(step_num, desc, log_entry, _cid=_cid, _title=_title)

        try:
            cr = await _run_single_case(
                runner=runner,
                run_uuid=run_uuid,
                run_id=run_id,
                case=case,
                lane_id=lane.lane_id,
                group_id=group_id,
                browser=lane.browser,
                app_url=app_url,
                username=username,
                password=password,
                use_google_signin=use_google_signin,
                headless=headless,
                progress_mgr=progress_mgr,
                on_step=_cb,
            )
        except Exception as exc:
            logger.exception(
                "[Execute] Lane %s case %s (%s) failed: %s",
                lane.lane_id, cid, tc_title, exc,
            )
            cr = CaseResult(
                test_case_id=cid,
                test_result_id=int(case.get("test_result_id") or 0),
                title=tc_title,
                status="error",
                duration_ms=0,
                step_results=[],
                adapted_steps=[],
                original_steps=list(case.get("steps") or []),
                agent_logs=[],
                screenshot_path=None,
                ai_modified={"steps": {}, "has_changes": False},
                error=str(exc),
                group_id=group_id,
                lane_id=lane.lane_id,
            )
        # Persist immediately so the case + its screenshots are viewable now.
        await persist_single_result(cr)
        async with results_lock:
            results_out.append(cr)
            live_completed.append(case_result_to_completed_dict(cr))
            if cr.get("screenshot_path") and cr["screenshot_path"] not in live_shots:
                live_shots.append(str(cr["screenshot_path"]))
            if len(live_shots) > 24:
                del live_shots[:-24]
            completed = len(results_out)
            total = int(state.get("total_cases") or 1)
            pct = min(99, int((completed / total) * 100))
            progress_mgr.update(
                run_id,
                {
                    "percentage": pct,
                    "current_test_case_index": completed,
                    "current_test_case_title": tc_title,
                    "active_lanes": pool.lane_snapshot(),
                    "completed_results": list(live_completed),
                    "live_screenshots": list(live_shots),
                },
            )
    await pool.release(lane, recycle=recycle_after_group)


async def execute_node(state: OrchestrationState) -> Dict[str, Any]:
    run_id = int(state["run_id"])
    run_uuid = state.get("run_uuid") or str(uuid.uuid4())
    progress_mgr = RunProgressManager()
    if progress_mgr.is_cancel_requested(run_id):
        return {"status": "cancelled", "cancel_requested": True}

    group_table = list(state.get("group_table") or [])

    from sqlalchemy import select
    from common.db.database import async_session_maker
    from features.functional.db.models.test_run_group import TestRunGroup, TestRunGroupStatus

    async with async_session_maker() as db:
        existing = await db.execute(
            select(TestRunGroup).where(TestRunGroup.test_run_id == run_id)
        )
        if not existing.scalars().first():
            for g in group_table:
                db.add(
                    TestRunGroup(
                        test_run_id=run_id,
                        group_id=str(g.get("group_id") or "G"),
                        title=str(g.get("title") or ""),
                        phase_order=g.get("phase_order"),
                        case_ids=g.get("case_ids") or [],
                        case_phases=g.get("case_phases"),
                        merged_steps=g.get("merged_steps"),
                        shared_login=bool(g.get("shared_login")),
                        status=TestRunGroupStatus.pending,
                    )
                )
            await db.commit()

    progress_mgr.update(
        run_id,
        {
            "groups": [
                {
                    "group_id": g.get("group_id"),
                    "title": g.get("title"),
                    "case_ids": g.get("case_ids"),
                    "status": "pending",
                }
                for g in group_table
            ],
            "current_test_case_title": "Executing grouped test cases…",
        },
    )
    headless = bool(state.get("headless"))
    # Fresh breaker + metrics for this run so a prior run's state can't leak in.
    gate = get_gate()
    gate.reset()
    pool = LanePool(headless=headless, lane_count=state.get("lane_count"))
    await pool.start()
    runner = TestCaseRunner()
    results_out: List[CaseResult] = []
    live_completed: List[Dict[str, Any]] = []
    live_shots: List[str] = []
    results_lock = asyncio.Lock()
    paused = {"value": False, "reason": ""}
    queue: asyncio.Queue = asyncio.Queue()
    for g in group_table:
        queue.put_nowait(g)

    async def _worker() -> None:
        while True:
            if progress_mgr.is_cancel_requested(run_id):
                break
            # PAUSE (don't fail) when the shared LLM circuit is open — the proxy
            # is down/over-budget. Stop pulling NEW work so we don't manufacture
            # hundreds of empty "error" results; un-run cases stay SKIPPED and
            # the run is resumable once the proxy recovers.
            if gate.should_pause():
                if not paused["value"]:
                    snap = gate.snapshot()
                    br = snap.get("breaker", {})
                    paused["value"] = True
                    paused["reason"] = (
                        "LLM budget exhausted" if br.get("budget_exhausted")
                        else f"LLM circuit open ({br.get('last_kind') or 'infra'})"
                    )
                    logger.error(
                        "[Execute] Pausing run %s — %s. Remaining cases left un-run "
                        "(resume after proxy recovers).", run_id, paused["reason"],
                    )
                break
            try:
                group = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            lane = await pool.acquire()
            try:
                await _execute_group_on_lane(
                    group, lane, pool, state, runner, run_uuid,
                    progress_mgr, results_out, results_lock,
                    live_completed, live_shots,
                )
            except Exception as exc:
                logger.exception("[Execute] Lane %s group failed: %s", lane.lane_id, exc)
                await pool.release(lane, recycle=True)

    worker_count = max(1, pool.lane_count)
    try:
        await asyncio.gather(*[_worker() for _ in range(worker_count)])
    finally:
        await pool.shutdown()

    if paused["value"]:
        progress_mgr.update(
            run_id,
            {
                "current_step_info": f"Paused: {paused['reason']}",
                "llm_gate": gate.snapshot(),
            },
        )

    # Only re-verify genuine failures. Infra errors (budget/circuit/timeout) are
    # NOT test failures — excluding them keeps the (expensive) vision-retry pass
    # from burning more budget on cases that never really ran.
    failed = [
        int(r["test_case_id"])
        for r in results_out
        if r.get("status") not in ("passed", "cancelled", "skipped")
        and not r.get("infra_error")
    ]
    return {
        "case_results": results_out,
        "failed_case_ids": failed,
        "active_lanes": [],
        "status": "evidence",
        "completed_count": len(results_out),
        "paused": paused["value"],
        "pause_reason": paused["reason"],
        "llm_gate": gate.snapshot(),
    }
