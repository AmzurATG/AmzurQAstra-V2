"""
Parallel Execution Orchestrator — runs all test cases via the three-phase agent pipeline:

  Phase 1 (PlannerAgent):   Full-step LLM plan — merges duplicate steps, assigns browser lanes.
  Phase 2 (SharedSessionRunner / TestCaseRunner): One browser per lane group.
  Phase 3 (EvaluatorAgent): Fan merged results back to each TC's step_results with screenshot_path.

Activated when execution_strategy == "grouped_parallel".  The default sequential path remains in
TestExecutionService._execute_background.  This orchestrator is called from there when the strategy
is set to grouped_parallel.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common.utils.logger import logger
from features.functional.core.browser.test_case_runner import TestCaseRunner
from features.functional.core.execution.execution_plan import ExecutionGroup, GroupedRunPlan, StepOriginMap
from features.functional.core.execution.planner_agent import build_execution_plan
from features.functional.core.execution.plan_safety_validator import validate_and_fix
from features.functional.core.execution.shared_session_runner import SharedSessionRunner
from features.functional.core.execution.evaluator_agent import evaluate_group_results
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.services.completed_result_builder import completed_case_dict
from features.functional.services.run_outcome import finalize_run_status
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.utils.credentials_redaction import (
    redact_agent_logs_list,
    redact_known_credentials,
    redact_step_dict,
)

from config import settings

# Configurable via settings/.env (MAX_CONCURRENT_BROWSERS). Must stay within your
# Steel plan's concurrent-session quota (free tier ≈ 1; pro = raise to 15-25).
MAX_CONCURRENT_BROWSERS = settings.MAX_CONCURRENT_BROWSERS


def _build_tc_full_payload(tc: TestCase) -> Dict[str, Any]:
    """Full per-case dict for PlannerAgent — includes all steps."""
    steps = [
        {
            "step_number": s.step_number,
            "action": s.action.value if hasattr(s.action, "value") else str(s.action),
            "target": s.target or "",
            "value": s.value or "",
            "description": s.description or "",
            "expected_result": s.expected_result or "",
        }
        for s in sorted(tc.steps, key=lambda x: x.step_number)
    ]
    first_step = ""
    if steps:
        s0 = steps[0]
        first_step = f"{s0['action']} {s0.get('target', '')} {s0.get('description', '')}".strip()
    return {
        "tc_id": tc.id,
        "title": tc.title or "",
        "description": (tc.description or "")[:300],
        "preconditions": (tc.preconditions or "")[:300],
        "scenario_type": tc.scenario_type or "positive",
        "priority": tc.priority.value if hasattr(tc.priority, "value") else str(tc.priority),
        "tags": tc.tags or "",
        "first_step": first_step[:150],
        "steps": steps,
    }


def _build_steps_data(tc: TestCase) -> List[Dict[str, Any]]:
    """Full step definitions for isolated runner and DB persistence."""
    return [
        {
            "step_number": s.step_number,
            "action": s.action.value if hasattr(s.action, "value") else str(s.action),
            "target": s.target,
            "value": s.value,
            "description": s.description,
            "expected_result": s.expected_result,
        }
        for s in sorted(tc.steps, key=lambda x: x.step_number)
    ]


class ParallelExecutionOrchestrator:
    """
    Orchestrates a grouped-parallel test run through PlannerAgent → Executors → EvaluatorAgent.
    """

    def __init__(self, db: AsyncSession, progress_manager: RunProgressManager) -> None:
        self.db = db
        self.pm = progress_manager

    async def execute(
        self,
        *,
        run_id: int,
        run: TestRun,
        ordered_results: List[TestResult],
        tc_map: Dict[int, TestCase],
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        headless: bool,
        log_fn: Callable[[str, Optional[int]], None],
    ) -> None:
        """Full pipeline for one run.  Mutates TestResult rows and TestRun counters."""
        run_uuid = str(uuid.uuid4())[:8]
        total = len(ordered_results)
        completed_results: List[Dict[str, Any]] = []

        # ── Phase 1: Build full payloads for PlannerAgent ─────────────────────
        tc_ids = [r.test_case_id for r in ordered_results]
        tc_full_payloads = [
            _build_tc_full_payload(tc_map[tc_id])
            for tc_id in tc_ids
            if tc_id in tc_map
        ]

        log_fn("🧠 PlannerAgent: analysing all steps and building merged execution plan…")
        self.pm.set(run_id, {
            "status": "planning",
            "percentage": 2,
            "current_test_case_index": 0,
            "total_test_cases": total,
            "current_test_case_title": "Building execution plan…",
            "current_step_info": "AI is merging duplicate steps and assigning browser lanes",
            "completed_results": [],
            "logs": list((self.pm.get(run_id) or {}).get("logs", [])),
            "error": None,
        })

        # ── Phase 1b: Plan + safety validation ───────────────────────────────
        # Build tc_summaries for safety validator (it only needs metadata)
        tc_summaries = [
            {k: v for k, v in p.items() if k != "steps"}
            for p in tc_full_payloads
        ]

        raw_plan, step_origin_map = await build_execution_plan(tc_full_payloads, app_url)
        plan = validate_and_fix(raw_plan, tc_summaries)
        # Rebuild origin map after safety validator may have reshuffled groups
        step_origin_map = plan.build_step_origin_map()

        # Persist plan
        cfg = dict(run.config or {})
        cfg["execution_plan"] = plan.to_dict()
        run.config = cfg
        await self.db.commit()

        groups_summary = ", ".join(
            f"{g.label}({g.session_type},lane={g.browser_lane})"
            for g in plan.groups
        )
        log_fn(
            f"✅ Execution plan: {len(plan.groups)} groups, "
            f"{plan.parallelism} parallel lanes — {groups_summary}"
        )
        self.pm.set(run_id, {
            "status": "running",
            "percentage": 5,
            "current_test_case_index": 0,
            "total_test_cases": total,
            "current_test_case_title": "Starting browser lanes…",
            "current_step_info": f"{len(plan.groups)} groups across {plan.parallelism} lanes",
            "completed_results": [],
            "logs": list((self.pm.get(run_id) or {}).get("logs", [])),
            "error": None,
            "execution_plan": plan.to_dict(),
        })

        # ── Phase 2+3 setup ──────────────────────────────────────────────────
        result_map: Dict[int, TestResult] = {r.test_case_id: r for r in ordered_results}
        tc_data: Dict[int, Dict[str, Any]] = {
            tc.id: {
                "title": tc.title or f"Case #{tc.id}",
                "description": tc.description or "",
                "preconditions": tc.preconditions or "",
                "steps": _build_steps_data(tc),
            }
            for tc in tc_map.values()
        }

        # Each group is an independent task guarded by the semaphore.
        # Within a lane, groups share one "lane slot" so they run sequentially on
        # that lane while other lanes proceed in parallel.  This gives us up to
        # MAX_CONCURRENT_BROWSERS browsers open at once across all lanes.
        lanes: Dict[int, List[ExecutionGroup]] = {}
        for g in plan.groups:
            lanes.setdefault(g.browser_lane, []).append(g)

        semaphore = asyncio.Semaphore(min(MAX_CONCURRENT_BROWSERS, max(plan.parallelism, 1)))
        completed_lock = asyncio.Lock()

        async def _run_lane(groups: List[ExecutionGroup]) -> None:
            """Run all groups in a single lane sequentially, each holding the semaphore."""
            for group in groups:
                if self.pm.is_cancel_requested(run_id):
                    # Cancel-requested: mark remaining cases in this lane as cancelled
                    async with completed_lock:
                        await self._mark_group_cancelled(
                            group=group,
                            tc_data=tc_data,
                            tc_map=tc_map,
                            result_map=result_map,
                            run_id=run_id,
                            total=total,
                            completed_results=completed_results,
                            log_fn=log_fn,
                        )
                    continue
                async with semaphore:
                    try:
                        await self._execute_group(
                            group=group,
                            tc_data=tc_data,
                            tc_map=tc_map,
                            result_map=result_map,
                            step_origin_map=step_origin_map,
                            app_url=app_url,
                            username=username,
                            password=password,
                            use_google_signin=use_google_signin,
                            headless=headless,
                            run_uuid=run_uuid,
                            run_id=run_id,
                            total=total,
                            completed_results=completed_results,
                            completed_lock=completed_lock,
                            log_fn=log_fn,
                        )
                    except Exception as exc:
                        logger.exception(
                            f"[Orchestrator] Group {group.group_id} crashed — "
                            f"marking {len(group.ordered_cases)} case(s) as ERROR. {exc}"
                        )
                        async with completed_lock:
                            await self._mark_group_error(
                                group=group,
                                error=str(exc),
                                tc_data=tc_data,
                                tc_map=tc_map,
                                result_map=result_map,
                                run_id=run_id,
                                total=total,
                                completed_results=completed_results,
                                log_fn=log_fn,
                            )

        lane_tasks = [_run_lane(groups) for groups in lanes.values()]
        await asyncio.gather(*lane_tasks, return_exceptions=True)

        # ── Finalize ─────────────────────────────────────────────────────────
        final_passed = sum(1 for r in completed_results if r.get("status") == "passed")
        final_failed = len(completed_results) - final_passed

        if self.pm.is_cancel_requested(run_id):
            run.status = TestRunStatus.CANCELLED
        else:
            run.status = TestRunStatus(
                finalize_run_status(
                    cancelled=False,
                    passed=final_passed,
                    failed=final_failed,
                    total=len(completed_results) or total,
                )
            )
        run.completed_at = datetime.utcnow()
        run.passed_tests = final_passed
        run.failed_tests = final_failed
        await self.db.commit()

        log_fn(f"Run complete — {final_passed} passed, {final_failed} failed (status={run.status.value})")
        self.pm.set(run_id, {
            "status": "cancelled" if self.pm.is_cancel_requested(run_id) else "completed",
            "percentage": 100,
            "current_test_case_index": total,
            "total_test_cases": total,
            "current_test_case_title": None,
            "current_step_info": "Completed",
            "completed_results": completed_results,
            "logs": list((self.pm.get(run_id) or {}).get("logs", [])),
            "error": None,
            "execution_plan": plan.to_dict(),
        })
        self.pm.clear_cancel(run_id)
        self.pm.schedule_cleanup(run_id, delay_seconds=300)

    async def _execute_group(
        self,
        *,
        group: ExecutionGroup,
        tc_data: Dict[int, Dict[str, Any]],
        tc_map: Dict[int, TestCase],
        result_map: Dict[int, TestResult],
        step_origin_map: StepOriginMap,
        app_url: str,
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        headless: bool,
        run_uuid: str,
        run_id: int,
        total: int,
        completed_results: List[Dict[str, Any]],
        completed_lock: asyncio.Lock,
        log_fn: Callable,
    ) -> None:
        """Execute one group and persist per-TC results via EvaluatorAgent."""
        log_fn(
            f"🚀 Lane {group.browser_lane} | {group.label} "
            f"[{group.session_type}] — {len(group.ordered_cases)} case(s), "
            f"{len(group.merged_steps)} merged steps"
        )

        # ── Phase 2: Execute ─────────────────────────────────────────────────
        group_result: Dict[str, Any] = {}  # populated by shared runner; used in persist block
        if group.is_shared and group.merged_steps:
            runner = SharedSessionRunner()
            group_result = await runner.run_group(
                group=group,
                app_url=app_url,
                username=username,
                password=password,
                use_google_signin=use_google_signin,
                headless=headless,
                run_uuid=run_uuid,
                execution_run_id=run_id,
            )
            # ── Phase 3: Evaluate — fan results to per-TC rows ──────────────
            tc_results = evaluate_group_results(
                group=group,
                group_result=group_result,
                step_origin_map=step_origin_map,
                tc_data=tc_data,
            )
        else:
            # Isolated: run each case in its OWN fresh browser, but via the SEGMENTED
            # runner (one original step at a time) so EVERY step gets a ground-truth
            # screenshot and a per-step pass/fail — even when the case fails (no 0/N).
            from features.functional.core.execution.execution_plan import MergedStep, PlannedCase
            tc_results: Dict[int, Dict[str, Any]] = {}
            seg_runner = SharedSessionRunner()
            for planned in sorted(group.ordered_cases, key=lambda c: c.order):
                if self.pm.is_cancel_requested(run_id):
                    tc_results[planned.tc_id] = {
                        "overall": "cancelled", "step_results": [], "screenshots": [],
                        "screenshot_path": None, "summary": "Run cancelled.",
                        "duration_ms": 0, "error": None,
                    }
                    continue
                tc_d = tc_data.get(planned.tc_id, {})
                steps = sorted(tc_d.get("steps", []), key=lambda x: x.get("step_number", 0))
                if not steps:
                    tc_results[planned.tc_id] = {
                        "overall": "error", "step_results": [], "screenshots": [],
                        "screenshot_path": None, "summary": "No steps to execute.",
                        "duration_ms": 0, "error": "No steps.",
                    }
                    continue

                # One synthetic single-case shared group: merged_steps == original steps.
                merged = [
                    MergedStep(
                        merged_step_number=s.get("step_number", i + 1),
                        action=s.get("action", "custom"),
                        description=s.get("description") or s.get("action", "") or "step",
                        target=s.get("target"), value=s.get("value"),
                        expected_result=s.get("expected_result"),
                        satisfies=[{"tc_id": planned.tc_id, "step_number": s.get("step_number", i + 1)}],
                    )
                    for i, s in enumerate(steps)
                ]
                syn_group = ExecutionGroup(
                    group_id=f"{group.group_id}_tc{planned.tc_id}",
                    label=(tc_d.get("title") or f"Case {planned.tc_id}")[:50],
                    session_type="shared",  # routes to segmented runner; opens its own browser
                    browser_lane=group.browser_lane,
                    reset_url=app_url,
                    ordered_cases=[PlannedCase(tc_id=planned.tc_id, order=1, reset_before=None,
                                               reason="isolated — segmented per step")],
                    merged_steps=merged,
                )
                syn_result = await seg_runner.run_group(
                    group=syn_group, app_url=app_url, username=username, password=password,
                    use_google_signin=use_google_signin, headless=headless, run_uuid=run_uuid,
                    execution_run_id=run_id,
                )
                syn_origin = {
                    f"{syn_group.group_id}:{ms.merged_step_number}": ms.satisfies for ms in merged
                }
                fanned = evaluate_group_results(
                    group=syn_group, group_result=syn_result,
                    step_origin_map=syn_origin, tc_data=tc_data,
                )
                tc_res_one = fanned.get(planned.tc_id, {
                    "overall": "error", "step_results": [], "screenshots": [],
                    "screenshot_path": None, "summary": syn_result.get("summary", ""),
                    "duration_ms": syn_result.get("duration_ms", 0),
                    "error": syn_result.get("error"),
                })
                # Evaluator already sliced logs; only fill if missing.
                if not tc_res_one.get("agent_logs"):
                    tc_res_one["agent_logs"] = syn_result.get("agent_logs", [])
                tc_results[planned.tc_id] = tc_res_one

        # ── Persist results ───────────────────────────────────────────────────
        async with completed_lock:
            for planned in group.ordered_cases:
                tc_id = planned.tc_id
                tc = tc_map.get(tc_id)
                test_result = result_map.get(tc_id)
                if not test_result:
                    continue

                tc_res = tc_results.get(tc_id, {})
                overall = tc_res.get("overall", "error")
                step_results = tc_res.get("step_results", [])
                steps_data = tc_data.get(tc_id, {}).get("steps", [])

                # Redact credentials from step results and build final list
                final_steps = [
                    redact_step_dict(s, username, password)
                    for s in step_results
                ]

                # Prefer per-case sliced logs from the evaluator (shared groups).
                raw_agent_logs = tc_res.get("agent_logs")
                if raw_agent_logs is None:
                    raw_agent_logs = (
                        group_result.get("agent_logs") if group.is_shared
                        else None
                    )
                safe_logs = redact_agent_logs_list(raw_agent_logs, username, password)

                shot_count = tc_res.get("agent_screenshot_count")
                if shot_count is None:
                    shot_count = sum(
                        1
                        for s in final_steps
                        if isinstance(s, dict) and s.get("screenshot_path")
                    )

                test_result.status = (
                    TestResultStatus.PASSED if overall == "passed"
                    else TestResultStatus.SKIPPED if overall == "cancelled"
                    else TestResultStatus.FAILED if overall == "failed"
                    else TestResultStatus.ERROR
                )
                test_result.duration_ms = tc_res.get("duration_ms", 0)
                test_result.started_at = datetime.utcnow()
                test_result.completed_at = datetime.utcnow()
                test_result.step_results = final_steps
                test_result.adapted_steps = [s for s in final_steps if s.get("adaptation")]
                test_result.original_steps = steps_data
                test_result.agent_logs = safe_logs
                test_result.screenshot_path = tc_res.get("screenshot_path")
                test_result.error_message = redact_known_credentials(
                    tc_res.get("error"), username=username, password=password
                )
                test_result.failed_step = next(
                    (s["step_number"] for s in final_steps if s.get("status") != "passed"), None
                )
                await self.db.commit()

                tc_title = (tc.title if tc else None) or f"Case #{tc_id}"
                share_note = ""
                if tc_res.get("shared_session") and tc_res.get("group_duration_ms"):
                    share_note = f" (shared group {tc_res.get('group_duration_ms')}ms)"
                log_fn(
                    f"{'✓' if overall == 'passed' else '✗'} [{group.label}] {tc_title} — "
                    f"{overall.upper()} ({tc_res.get('duration_ms', 0)}ms){share_note} "
                    f"shots={shot_count}",
                    tc_id,
                )

                cur_done = len(completed_results) + 1
                case_payload = completed_case_dict(
                    test_result_id=test_result.id,
                    test_case_id=tc_id,
                    title=tc_title,
                    status=overall,
                    steps_total=len(final_steps),
                    steps_passed=sum(1 for s in final_steps if s.get("status") == "passed"),
                    steps_failed=sum(1 for s in final_steps if s.get("status") != "passed"),
                    duration_ms=tc_res.get("duration_ms", 0),
                    step_results=final_steps,
                    adapted_steps=[s for s in final_steps if s.get("adaptation")],
                    original_steps=steps_data,
                    agent_logs=safe_logs,
                    screenshot_path=test_result.screenshot_path,
                    failed_step=test_result.failed_step,
                    agent_screenshot_count=int(shot_count or 0),
                    shared_session=bool(tc_res.get("shared_session")),
                    group_duration_ms=tc_res.get("group_duration_ms"),
                )
                # Store lite summaries in progress RAM for large runs; full detail via result API.
                if settings.LIVE_PROGRESS_STORE_LITE:
                    from features.functional.services.completed_result_builder import (
                        completed_case_to_lite,
                    )
                    completed_results.append(completed_case_to_lite(case_payload))
                else:
                    completed_results.append(case_payload)

                self.pm.set(run_id, {
                    "status": "running",
                    "percentage": min(99, int((cur_done / max(total, 1)) * 100)),
                    "current_test_case_index": cur_done,
                    "total_test_cases": total,
                    "current_test_case_title": tc_title,
                    "current_step_info": f"Lane {group.browser_lane}: {group.label}",
                    "completed_results": list(completed_results),
                    "logs": list((self.pm.get(run_id) or {}).get("logs", [])),
                    "error": None,
                })

    @staticmethod
    def _attach_screenshots_to_steps(
        step_results: List[Dict[str, Any]],
        agent_logs: List[Dict[str, Any]],
    ) -> None:
        """For isolated runs: distribute agent_log screenshots across step_result rows."""
        if not agent_logs or not step_results:
            return
        logs_with_shots = [l for l in agent_logs if l.get("screenshot_path")]
        if not logs_with_shots:
            return
        total_steps = len(step_results)
        total_shots = len(logs_with_shots)
        for idx, step in enumerate(step_results):
            start_i = int(idx * total_shots / total_steps)
            end_i = int((idx + 1) * total_shots / total_steps)
            slice_logs = logs_with_shots[start_i:end_i]
            if slice_logs:
                step["screenshot_path"] = slice_logs[-1]["screenshot_path"]

    @staticmethod
    def _pick_primary_screenshot(
        step_results: List[Dict[str, Any]],
        screenshots: List[str],
    ) -> Optional[str]:
        """Return the screenshot of the first failed step, or last screenshot if all passed."""
        for s in step_results:
            if s.get("status") not in ("passed",) and s.get("screenshot_path"):
                return s["screenshot_path"]
        if screenshots:
            return screenshots[-1]
        return None

    async def _mark_group_cancelled(
        self,
        *,
        group: ExecutionGroup,
        tc_data: Dict[int, Dict[str, Any]],
        tc_map: Dict[int, TestCase],
        result_map: Dict[int, TestResult],
        run_id: int,
        total: int,
        completed_results: List[Dict[str, Any]],
        log_fn: Callable,
    ) -> None:
        """Mark all cases in a group as CANCELLED after a cancel request."""
        await self._mark_group_with_status(
            group=group,
            overall="cancelled",
            error_msg=None,
            tc_data=tc_data,
            tc_map=tc_map,
            result_map=result_map,
            run_id=run_id,
            total=total,
            completed_results=completed_results,
            log_fn=log_fn,
        )

    async def _mark_group_error(
        self,
        *,
        group: ExecutionGroup,
        error: str,
        tc_data: Dict[int, Dict[str, Any]],
        tc_map: Dict[int, TestCase],
        result_map: Dict[int, TestResult],
        run_id: int,
        total: int,
        completed_results: List[Dict[str, Any]],
        log_fn: Callable,
    ) -> None:
        """Mark all cases in a group as ERROR after an unexpected exception."""
        await self._mark_group_with_status(
            group=group,
            overall="error",
            error_msg=error,
            tc_data=tc_data,
            tc_map=tc_map,
            result_map=result_map,
            run_id=run_id,
            total=total,
            completed_results=completed_results,
            log_fn=log_fn,
        )

    async def _mark_group_with_status(
        self,
        *,
        group: ExecutionGroup,
        overall: str,
        error_msg: Optional[str],
        tc_data: Dict[int, Dict[str, Any]],
        tc_map: Dict[int, TestCase],
        result_map: Dict[int, TestResult],
        run_id: int,
        total: int,
        completed_results: List[Dict[str, Any]],
        log_fn: Callable,
    ) -> None:
        """Persist a uniform status for every case in a group that has no result yet."""
        db_status = (
            TestResultStatus.SKIPPED if overall == "cancelled"
            else TestResultStatus.ERROR
        )
        for planned in group.ordered_cases:
            tc_id = planned.tc_id
            test_result = result_map.get(tc_id)
            if not test_result:
                continue
            # Only update cases that haven't been written yet (still SKIPPED placeholder)
            if test_result.status not in (TestResultStatus.SKIPPED,):
                continue
            tc = tc_map.get(tc_id)
            tc_d = tc_data.get(tc_id, {})
            steps_data = tc_d.get("steps", [])

            test_result.status = db_status
            test_result.duration_ms = 0
            test_result.started_at = datetime.utcnow()
            test_result.completed_at = datetime.utcnow()
            test_result.step_results = []
            test_result.original_steps = steps_data
            test_result.error_message = error_msg
            await self.db.commit()

            tc_title = (tc.title if tc else None) or f"Case #{tc_id}"
            log_fn(
                f"{'⊘' if overall == 'cancelled' else '✗'} [{group.label}] {tc_title} — "
                f"{overall.upper()} (not executed)",
                tc_id,
            )

            cur_done = len(completed_results) + 1
            completed_results.append(
                completed_case_dict(
                    test_result_id=test_result.id,
                    test_case_id=tc_id,
                    title=tc_title,
                    status=overall,
                    steps_total=len(steps_data),
                    steps_passed=0,
                    steps_failed=0,
                    duration_ms=0,
                    step_results=[],
                    adapted_steps=[],
                    original_steps=steps_data,
                    agent_logs=None,
                    screenshot_path=None,
                )
            )
            self.pm.set(run_id, {
                "status": "running",
                "percentage": min(99, int((cur_done / max(total, 1)) * 100)),
                "current_test_case_index": cur_done,
                "total_test_cases": total,
                "current_test_case_title": tc_title,
                "current_step_info": f"Lane {group.browser_lane}: {group.label}",
                "completed_results": list(completed_results),
                "logs": list((self.pm.get(run_id) or {}).get("logs", [])),
                "error": None,
            })
