"""Execute node: dispatch groups across lane pool with watchdog + consistency."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from features.functional.core.browser.test_case_runner import TestCaseRunner
from features.functional.core.browser.llm_gate import get_gate
from features.functional.core.grouping.setup_step_merger import (
    extract_setup_donor_evidence,
    merge_step_results_with_skipped_setup,
    prepare_steps_for_shared_session,
)
from features.functional.core.memory.store import append_event
from features.functional.core.run_governor import RunGovernor
from features.functional.core.screenshots import ScreenshotAgent
from features.functional.core.status_narrator import narrate_case_result
from features.functional.core.supervisor.watchdog import LaneWatchdog
from config import settings
from features.functional.core.ui_consistency.agent import UiConsistencyAgent
from features.functional.core.ui_consistency.rules import detect_desync
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
    steps_override: Optional[List[Dict[str, Any]]] = None,
    session_context: Optional[str] = None,
    extra_prompt_hint: Optional[str] = None,
    skipped_setup: Optional[List[Dict[str, Any]]] = None,
    reassign_count: int = 0,
) -> CaseResult:
    tc_id = int(case["test_case_id"])
    original_steps = list(case.get("steps") or [])
    run_steps = list(steps_override if steps_override is not None else original_steps)
    from features.functional.core.case_budget import budget_for_case

    budget = budget_for_case(run_steps, reassign_count=reassign_count)
    result = await runner.run(
        run_id=run_uuid,
        test_case_id=tc_id,
        title=str(case.get("title") or ""),
        description=str(case.get("description") or ""),
        preconditions=str(case.get("preconditions") or ""),
        steps=run_steps,
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
        session_context=session_context,
        extra_prompt_hint=extra_prompt_hint,
        wallclock_timeout_s=int(budget["wallclock_timeout_s"]),
        reassign_count=reassign_count,
    )
    tc_status = result.get("overall", "error")
    # Normalize infra/error payloads before merge so steps are never silently empty.
    result = narrate_case_result(result, original_steps)
    tc_status = result.get("overall", tc_status)
    llm_steps = {s.get("step_number"): s for s in result.get("step_results", [])}
    skipped = list(skipped_setup or [])
    if result.get("infra_error") and result.get("step_results"):
        final_steps = [
            redact_step_dict(dict(s), username, password)
            for s in result["step_results"]
            if isinstance(s, dict)
        ]
    elif skipped:
        final_steps = merge_step_results_with_skipped_setup(
            original_steps,
            skipped,
            list(result.get("step_results") or []),
            overall_status=tc_status,
            summary=str(result.get("summary") or ""),
        )
    else:
        final_steps = []
        for s_orig in original_steps:
            num = s_orig.get("step_number")
            s_res = llm_steps.get(num, {})
            merged = {
                **s_orig,
                "status": s_res.get("status", "skipped"),
                "actual_result": s_res.get("actual_result"),
                "adaptation": s_res.get("adaptation"),
            }
            if s_res.get("infra_blocked"):
                merged["infra_blocked"] = True
            final_steps.append(redact_step_dict(merged, username, password))

    ai_modified: Dict[str, Any] = {"steps": {}, "has_changes": False}
    for redacted in final_steps:
        if redacted.get("adaptation"):
            ai_modified["has_changes"] = True
            ai_modified["steps"][str(redacted.get("step_number"))] = redacted.get("adaptation")
    if result.get("verdict_source"):
        ai_modified["verdict_source"] = result.get("verdict_source")
    if result.get("user_message"):
        ai_modified["user_message"] = result.get("user_message")
    if result.get("infra_error"):
        ai_modified["infra_error"] = True
        ai_modified["error_kind"] = result.get("error_kind")
    if reassign_count:
        ai_modified["reassign_count"] = reassign_count
        ai_modified["reassign_history"] = list(
            (case.get("_reassign_history") or []) + [{"count": reassign_count}]
        )

    safe_logs = redact_agent_logs_list(result.get("logs"), username, password) or []
    shots = list(result.get("screenshots") or [])
    # Ensure curation even if runner path skipped it (e.g. error payloads).
    curated = ScreenshotAgent.curate(
        safe_logs,
        shots,
        overall=tc_status,
    )
    safe_logs = curated["agent_logs"]
    shots = curated["screenshots"]
    evidence_count = curated["evidence_screenshot_count"]
    return CaseResult(
        test_case_id=tc_id,
        test_result_id=int(case.get("test_result_id") or 0),
        title=str(case.get("title") or ""),
        status=tc_status,
        duration_ms=int(result.get("duration_ms") or 0),
        step_results=final_steps,
        adapted_steps=[s for s in final_steps if s.get("adaptation")],
        original_steps=original_steps,
        agent_logs=safe_logs,
        screenshot_path=curated.get("screenshot_path") or (shots[-1] if shots else None),
        ai_modified={
            **ai_modified,
            "evidence_screenshot_count": evidence_count,
            "raw_screenshot_count": curated.get("raw_screenshot_count"),
        },
        error=redact_known_credentials(
            result.get("error"), username=username, password=password
        ),
        error_kind=result.get("error_kind"),
        infra_error=bool(result.get("infra_error")),
        group_id=group_id,
        lane_id=lane_id,
        verdict_source=result.get("verdict_source"),
        reassign_count=reassign_count,
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
    watchdog: LaneWatchdog,
    consistency: UiConsistencyAgent,
    reassign_queue: asyncio.Queue,
    reassign_counts: Dict[int, int],
) -> None:
    run_id = int(state["run_id"])
    case_map = _cases_by_id(state)
    app_url = state.get("app_url") or ""
    username = state.get("username")
    password = state.get("password")
    use_google_signin = bool(state.get("use_google_signin"))
    headless = bool(state.get("headless"))
    extra_hint = str(state.get("recon_prompt_hint") or "") or None
    group_id = str(group.get("group_id") or "G")
    lane.current_group_id = group_id
    case_ids = sorted(
        [int(x) for x in (group.get("case_ids") or [])],
        key=lambda cid: _phase_sort_key(group, cid),
    )

    async def _on_step(step_num, desc, log_entry, *, _cid=None, _title=""):
        if _cid is not None:
            watchdog.heartbeat(int(_cid))
            lane.last_heartbeat_at = time.monotonic()
        shot = log_entry.get("screenshot_path") if log_entry else None
        lanes = pool.lane_snapshot()
        for ln in lanes:
            if ln["lane_id"] == lane.lane_id:
                ln["title"] = _title or group_id
                ln["step"] = desc
                ln["test_case_id"] = _cid
                ln["step_num"] = step_num
                ln["last_heartbeat_at"] = lane.last_heartbeat_at
        progress_mgr.update(
            run_id,
            {
                "active_lanes": lanes,
                "current_step_info": f"Lane {lane.lane_id}: {desc}",
            },
        )

    recycle_after_group = bool(group.get("shared_login"))
    session_warm = False
    donor_setup_steps: List[Dict[str, Any]] = []
    donor_screenshot_path: Optional[str] = None
    governor = RunGovernor() if bool(getattr(settings, "RUN_GOVERNOR_ENABLED", True)) else None
    for cid in case_ids:
        if progress_mgr.is_cancel_requested(run_id):
            break
        if governor is not None:
            gd = await governor.apply_before_case(run_id=run_id, progress_mgr=progress_mgr)
            if gd.action == "pause":
                logger.error("[RunGovernor] Pausing lane %s dispatch: %s", lane.lane_id, gd.reason)
                progress_mgr.update(
                    run_id,
                    {
                        "runtime_banner": gd.banner
                        or {
                            "level": "warning",
                            "message": "AI service unavailable — run paused. Retry later.",
                        },
                        "status": "paused",
                    },
                )
                break
            health_line = governor.health_prompt_hint()
            if health_line:
                extra_hint = (
                    f"{extra_hint}\n\n{health_line}" if extra_hint else health_line
                )
        case = case_map.get(cid)
        if not case:
            continue
        tc_title = str(case.get("title") or f"Case {cid}")
        prior_reassigns = int(reassign_counts.get(cid, 0))

        async def _cb(step_num, desc, log_entry, _cid=cid, _title=tc_title):
            await _on_step(step_num, desc, log_entry, _cid=_cid, _title=_title)

        steps_override = None
        session_context = None
        skipped_setup: list = []
        if recycle_after_group and session_warm:
            steps_override, skipped_setup, session_context = prepare_steps_for_shared_session(
                list(case.get("steps") or []),
                session_warm=True,
                donor_setup_steps=donor_setup_steps,
                donor_screenshot_path=donor_screenshot_path,
            )

        watchdog.start_case(
            test_case_id=cid,
            lane_id=lane.lane_id,
            reassign_count=prior_reassigns,
            title=tc_title,
        )
        lane.case_started_at = time.monotonic()
        lane.current_case_id = cid
        lane.last_heartbeat_at = time.monotonic()

        case_task = asyncio.create_task(
            _run_single_case(
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
                steps_override=steps_override,
                session_context=session_context,
                extra_prompt_hint=extra_hint,
                skipped_setup=skipped_setup,
                reassign_count=prior_reassigns,
            )
        )

        cr: Optional[CaseResult] = None
        reassigned = False
        try:
            while not case_task.done():
                decision = watchdog.evaluate(cid)
                if decision.action == "reassign" and watchdog.can_reassign(cid):
                    case_task.cancel()
                    try:
                        await case_task
                    except (asyncio.CancelledError, Exception):
                        pass
                    new_count = watchdog.record_reassign(
                        test_case_id=cid,
                        reason=decision.reason,
                        from_lane=lane.lane_id,
                    )
                    reassign_counts[cid] = new_count
                    # Solo requeue so shared-session assumptions don't leak
                    solo = GroupRow(
                        group_id=f"{group_id}_re_{cid}_{new_count}",
                        parent_group_id=group.get("parent_group_id") or group_id,
                        title=f"{tc_title} (reassign {new_count})",
                        phase_order=["authed"],
                        case_ids=[cid],
                        case_phases={str(cid): "authed"},
                        merged_steps={},
                        shared_login=False,
                        status="pending",
                    )
                    await reassign_queue.put(solo)
                    project_id = int(state.get("project_id") or 0)
                    if project_id:
                        append_event(
                            project_id,
                            {
                                "type": "slow_case_reassign",
                                "test_case_id": cid,
                                "reason": decision.reason,
                                "run_id": run_id,
                            },
                            hint=f"Case {cid} was slow/stale — prefer tighter scopes or fresh lane.",
                        )
                    await pool._recycle_lane(lane)
                    reassigned = True
                    logger.warning(
                        "[Watchdog] Reassigning case %s from lane %s (%s)",
                        cid, lane.lane_id, decision.reason,
                    )
                    break
                try:
                    cr = await asyncio.wait_for(asyncio.shield(case_task), timeout=5.0)
                    break
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    raise
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

        if reassigned:
            watchdog.finish_case(cid)
            continue

        if cr is None and case_task.done():
            try:
                cr = case_task.result()
            except Exception as exc:
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

        watchdog.finish_case(cid)
        if cr and cr.get("infra_error"):
            q = watchdog.record_infra_failure(lane.lane_id)
            if q.action == "quarantine_lane":
                lane.quarantined = True
                await pool._recycle_lane(lane)
                watchdog.clear_quarantine(lane.lane_id)
                lane.quarantined = False

        if cr:
            await persist_single_result(cr)
            async with results_lock:
                # Drop prior incomplete result for same case (reassign path)
                results_out[:] = [
                    r for r in results_out if int(r.get("test_case_id") or 0) != cid
                ]
                live_completed[:] = [
                    r for r in live_completed if int(r.get("test_case_id") or 0) != cid
                ]
                results_out.append(cr)
                entry = case_result_to_completed_dict(cr)
                live_completed.append(entry)
                if cr.get("screenshot_path") and cr["screenshot_path"] not in live_shots:
                    live_shots.append(str(cr["screenshot_path"]))
                if len(live_shots) > 24:
                    del live_shots[:-24]
                completed = len(results_out)
                total = int(state.get("total_cases") or 1)
                pct = min(99, int((completed / total) * 100))
                desync_hit = detect_desync(entry) is not None
                progress_mgr.update(
                    run_id,
                    {
                        "percentage": pct,
                        "current_test_case_index": completed,
                        "current_test_case_title": tc_title,
                        "active_lanes": pool.lane_snapshot(),
                        "completed_results": list(live_completed),
                        "live_screenshots": list(live_shots),
                        "watchdog": watchdog.snapshot(),
                    },
                )
                if consistency.should_run(completed_count=completed, desync_hit=desync_hit):
                    await consistency.sweep(
                        run_id,
                        live_completed=list(live_completed),
                        progress_mgr=progress_mgr,
                    )
                    # Refresh local list after patch
                    body = progress_mgr.get(run_id) or {}
                    if body.get("completed_results"):
                        live_completed[:] = list(body["completed_results"])

        if recycle_after_group and cr and cr.get("status") in ("passed", "failed", "error"):
            session_warm = True
            # Capture login evidence from the first case so later cases show full setup detail.
            if not donor_setup_steps:
                donor_setup_steps, donor_screenshot_path = extract_setup_donor_evidence(
                    cr.get("step_results"),
                    cr.get("agent_logs"),
                    cr.get("screenshot_path"),
                )

    await pool.release(lane, recycle=recycle_after_group)


async def execute_node(state: OrchestrationState) -> Dict[str, Any]:
    run_id = int(state["run_id"])
    run_uuid = state.get("run_uuid") or str(uuid.uuid4())
    progress_mgr = RunProgressManager()
    if progress_mgr.is_cancel_requested(run_id):
        return {"status": "cancelled", "cancel_requested": True}
    if state.get("status") == "error":
        return {"status": "error", "error": state.get("error"), "case_results": []}

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
                        parent_group_id=g.get("parent_group_id"),
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
                    "parent_group_id": g.get("parent_group_id"),
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
    gate = get_gate()
    gate.reset()
    requested = int(state.get("lane_count") or 6)
    pool = LanePool(headless=headless, lane_count=requested)
    await pool.start()
    if pool.lane_count < 1:
        msg = f"Lane contract failed: expected lanes but pool started with {pool.lane_count}"
        progress_mgr.update(run_id, {"status": "error", "error": msg})
        await pool.shutdown()
        return {"status": "error", "error": msg, "case_results": []}

    runner = TestCaseRunner()
    results_out: List[CaseResult] = []
    live_completed: List[Dict[str, Any]] = []
    live_shots: List[str] = []
    results_lock = asyncio.Lock()
    paused = {"value": False, "reason": ""}
    queue: asyncio.Queue = asyncio.Queue()
    reassign_queue: asyncio.Queue = asyncio.Queue()
    reassign_counts: Dict[int, int] = {}
    watchdog = LaneWatchdog()
    consistency = UiConsistencyAgent()
    for g in group_table:
        queue.put_nowait(g)

    worker_count = max(1, pool.lane_count)
    inflight = {"n": 0}

    async def _worker() -> None:
        while True:
            if progress_mgr.is_cancel_requested(run_id):
                break
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
            group = None
            try:
                group = reassign_queue.get_nowait()
            except asyncio.QueueEmpty:
                try:
                    group = queue.get_nowait()
                except asyncio.QueueEmpty:
                    if inflight["n"] > 0:
                        await asyncio.sleep(0.2)
                        continue
                    try:
                        group = await asyncio.wait_for(reassign_queue.get(), timeout=0.3)
                    except (asyncio.TimeoutError, asyncio.QueueEmpty):
                        break
            inflight["n"] += 1
            lane = await pool.acquire()
            try:
                await _execute_group_on_lane(
                    group, lane, pool, state, runner, run_uuid,
                    progress_mgr, results_out, results_lock,
                    live_completed, live_shots,
                    watchdog, consistency, reassign_queue, reassign_counts,
                )
            except Exception as exc:
                logger.exception("[Execute] Lane %s group failed: %s", lane.lane_id, exc)
                await pool.release(lane, recycle=True)
            finally:
                inflight["n"] -= 1

    try:
        await asyncio.gather(*[_worker() for _ in range(worker_count)])
    finally:
        # Final consistency sweep before evidence
        try:
            await consistency.sweep(
                run_id,
                live_completed=list(live_completed),
                progress_mgr=progress_mgr,
            )
        except Exception as exc:
            logger.warning("[UiConsistency] final sweep failed: %s", exc)
        await pool.shutdown()

    if paused["value"]:
        progress_mgr.update(
            run_id,
            {
                "current_step_info": f"Paused: {paused['reason']}",
                "llm_gate": gate.snapshot(),
            },
        )

    failed = [
        int(r["test_case_id"])
        for r in results_out
        if r.get("status") not in ("passed", "cancelled", "skipped")
        and not r.get("infra_error")
    ]
    body = progress_mgr.get(run_id) or {}
    return {
        "case_results": results_out,
        "failed_case_ids": failed,
        "active_lanes": [],
        "status": "evidence",
        "completed_count": len(results_out),
        "paused": paused["value"],
        "pause_reason": paused["reason"],
        "llm_gate": gate.snapshot(),
        "watchdog": watchdog.snapshot(),
        "ui_desync_events": list(body.get("ui_desync_events") or []),
    }
