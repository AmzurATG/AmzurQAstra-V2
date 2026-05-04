"""
Test Execution Service — orchestrates test runs via browser-use.
Each test case runs sequentially with an isolated browser (fresh session per case)
so batch runs match single-case behavior (no shared login/DOM state).
"""
import asyncio
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from common.api.pagination import PaginationParams
from common.utils.logger import logger
from common.db.models.project import Project
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.schemas.test_run import TestRunCreate
from features.functional.core.browser.test_case_runner import (
    TestCaseRunner,
    cleanup_tc_progress,
)
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.services.completed_result_builder import completed_case_dict
from features.functional.services.test_run_stats import fetch_test_run_summary
from features.functional.services import test_result_evidence
from features.functional.utils.credentials_redaction import (
    redact_agent_logs_list,
    redact_known_credentials,
    redact_step_dict,
)

# India Standard Time (no DST); avoids tzdata/zoneinfo issues on minimal Windows installs.
_IST = timezone(timedelta(hours=5, minutes=30))


async def _mark_remaining_skipped(
    db: AsyncSession,
    ordered_results: List[TestResult],
    start_idx: int,
    tc_map: Dict[int, TestCase],
    reason: str,
    completed_results: List[Dict[str, Any]],
) -> None:
    """Mark not-yet-finished results as skipped and append to live progress list."""
    for j in range(start_idx, len(ordered_results)):
        tr = ordered_results[j]
        if tr.status in (
            TestResultStatus.PASSED,
            TestResultStatus.FAILED,
            TestResultStatus.ERROR,
        ):
            continue
        tc = tc_map.get(tr.test_case_id)
        tc_title = (tc.title if tc else None) or f"Test Case #{tr.test_case_id}"
        tr.status = TestResultStatus.SKIPPED
        tr.error_message = reason
        tr.completed_at = datetime.utcnow()
        tr.duration_ms = tr.duration_ms or 0
        tr.step_results = []
        tr.failed_step = None
        completed_results.append(
            completed_case_dict(
                test_result_id=tr.id,
                test_case_id=tr.test_case_id,
                title=tc_title,
                status="skipped",
                steps_total=0,
                steps_passed=0,
                steps_failed=0,
                duration_ms=0,
                step_results=[],
                adapted_steps=[],
                original_steps=[],
                agent_logs=None,
                screenshot_path=None,
            )
        )
    await db.commit()


class TestExecutionService:
    """Manages test run lifecycle: create → execute (background) → poll → results."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.progress_manager = RunProgressManager()

    async def _next_run_number(self, project_id: int) -> int:
        """Next per-project run index (1-based), stable for display (unlike global `id`)."""
        r = await self.db.execute(
            select(func.coalesce(func.max(TestRun.run_number), 0)).where(
                TestRun.project_id == project_id
            )
        )
        return int(r.scalar() or 0) + 1

    async def get_runs(
        self,
        project_id: int,
        status: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[TestRun], int]:
        query = select(TestRun).where(TestRun.project_id == project_id)
        count_q = select(func.count(TestRun.id)).where(TestRun.project_id == project_id)

        if status == "failed":
            query = query.where(
                TestRun.status.in_((TestRunStatus.FAILED, TestRunStatus.ERROR))
            )
            count_q = count_q.where(
                TestRun.status.in_((TestRunStatus.FAILED, TestRunStatus.ERROR))
            )
        elif status:
            try:
                st = TestRunStatus(status)
            except ValueError:
                st = None
            if st is not None:
                query = query.where(TestRun.status == st)
                count_q = count_q.where(TestRun.status == st)

        total = (await self.db.execute(count_q)).scalar() or 0

        query = query.order_by(TestRun.run_number.desc(), TestRun.id.desc())

        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)

        return list((await self.db.execute(query)).scalars().all()), total

    async def get_run_summary(self, project_id: int) -> Dict[str, Any]:
        return await fetch_test_run_summary(self.db, project_id)

    async def get_run_with_results(self, run_id: int) -> Optional[TestRun]:
        result = await self.db.execute(
            select(TestRun)
            .options(
                selectinload(TestRun.test_results).selectinload(TestResult.test_case),
            )
            .where(TestRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def create_run(
        self, run_data: TestRunCreate, triggered_by: int
    ) -> TestRun:
        if run_data.test_case_ids:
            tc_result = await self.db.execute(
                select(TestCase)
                .where(TestCase.id.in_(run_data.test_case_ids))
                .where(TestCase.project_id == run_data.project_id)
            )
            by_id = {tc.id: tc for tc in tc_result.scalars().all()}
            # Preserve client order (SQL IN does not guarantee order)
            test_cases = [by_id[i] for i in run_data.test_case_ids if i in by_id]
        else:
            tc_result = await self.db.execute(
                select(TestCase)
                .where(TestCase.project_id == run_data.project_id)
                .order_by(TestCase.id)
            )
            test_cases = list(tc_result.scalars().all())

        run_number = await self._next_run_number(run_data.project_id)
        test_run = TestRun(
            project_id=run_data.project_id,
            run_number=run_number,
            name=run_data.name
            or f"Test Run {datetime.now(_IST).strftime('%Y-%m-%d %H:%M')} IST",
            description=run_data.description,
            status=TestRunStatus.PENDING,
            triggered_by=triggered_by,
            total_tests=len(test_cases),
            browser=run_data.browser,
            headless=str(run_data.headless).lower(),
            config={
                "app_url": run_data.app_url,
                "use_google_signin": run_data.use_google_signin,
                "has_credentials": run_data.credentials is not None,
            },
        )
        self.db.add(test_run)
        await self.db.flush()

        for tc in test_cases:
            self.db.add(TestResult(
                test_run_id=test_run.id,
                test_case_id=tc.id,
                status=TestResultStatus.SKIPPED,
            ))
        await self.db.commit()
        await self.db.refresh(test_run)
        return test_run

    async def start_execution(self, run_id: int, run_data: TestRunCreate) -> None:
        """Launch a background task. Falls back to project-level credentials if not provided."""
        app_url = (run_data.app_url or "").strip() or None
        username = run_data.credentials.username if run_data.credentials else None
        password = run_data.credentials.password if run_data.credentials else None

        proj = (await self.db.execute(
            select(Project).where(Project.id == run_data.project_id)
        )).scalar_one_or_none()
        if proj:
            if not app_url and proj.app_url:
                app_url = (proj.app_url or "").strip() or None
            creds = proj.app_credentials or {}
            if (not username or not password) and creds:
                if not username:
                    username = creds.get("username")
                if not password:
                    password = creds.get("password")
        
        # Ensure credentials are passed correctly even if mixed
        final_creds = {
            "username": username,
            "password": password
        }

        # Persist resolved app URL on the run so DB / retries reflect what automation will use
        run_row = (await self.db.execute(select(TestRun).where(TestRun.id == run_id))).scalar_one_or_none()
        if run_row is not None:
            cfg = dict(run_row.config or {})
            if app_url:
                cfg["app_url"] = app_url
            run_row.config = cfg
            await self.db.commit()

        if sys.platform == "win32":
            # On Windows, we must run the background execution in a separate thread
            # with a ProactorEventLoop to support subprocesses (browser-use launches Chrome).
            asyncio.create_task(
                asyncio.to_thread(
                    self._run_background_sync,
                    run_id,
                    app_url=app_url,
                    username=final_creds["username"],
                    password=final_creds["password"],
                    use_google_signin=run_data.use_google_signin,
                    headless=run_data.headless,
                )
            )
        else:
            asyncio.create_task(
                self._execute_background(
                    run_id,
                    app_url=app_url,
                    username=final_creds["username"],
                    password=final_creds["password"],
                    use_google_signin=run_data.use_google_signin,
                    headless=run_data.headless,
                )
            )

    def _run_background_sync(self, *args: Any, **kwargs: Any) -> None:
        """Synchronous wrapper to run the background task in a new event loop on Windows."""
        # Ensure we use ProactorEventLoop on Windows for subprocess support
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        loop = policy.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute_background(*args, **kwargs))
        finally:
            loop.close()

    async def _execute_background(
        self,
        run_id: int,
        app_url: Optional[str],
        username: Optional[str],
        password: Optional[str],
        use_google_signin: bool,
        headless: bool,
    ) -> None:
        from common.db.database import async_session_maker

        run_uuid = str(uuid.uuid4())[:8]
        logs: List[Dict[str, Any]] = []

        def _log(msg: str, tc_id: Optional[int] = None) -> None:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": msg,
                "test_case_id": tc_id,
            }
            logs.append(log_entry)
            self.progress_manager.add_log(run_id, log_entry)

        async with async_session_maker() as db:
            try:
                run = (await db.execute(
                    select(TestRun)
                    .options(selectinload(TestRun.test_results))
                    .where(TestRun.id == run_id)
                )).scalar_one_or_none()
                if not run:
                    return

                if run.status == TestRunStatus.CANCELLED:
                    _log("Run was cancelled before execution started.")
                    self.progress_manager.set(run_id, {
                        "status": "cancelled",
                        "percentage": 100,
                        "current_test_case_index": 0,
                        "total_test_cases": len(run.test_results or []),
                        "current_test_case_title": None,
                        "current_step_info": None,
                        "completed_results": [],
                        "logs": list(logs),
                        "error": None,
                    })
                    self.progress_manager.clear_cancel(run_id)
                    self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
                    return

                run.status = TestRunStatus.RUNNING
                run.started_at = datetime.utcnow()
                await db.commit()

                # Resolve URL: thread arg first, then persisted run config (create_run may have stored null)
                cfg = run.config or {}
                app_url_eff = (app_url or "").strip() if app_url else ""
                if not app_url_eff and cfg.get("app_url"):
                    app_url_eff = str(cfg["app_url"]).strip()
                if not app_url_eff:
                    _log("✗ No application URL configured. Set App URL on the project (Settings) or ensure the run request includes app_url.")
                    run.status = TestRunStatus.ERROR
                    run.completed_at = datetime.utcnow()
                    await db.commit()
                    self.progress_manager.set(run_id, {
                        "status": "error",
                        "percentage": 100,
                        "current_test_case_index": 0,
                        "total_test_cases": 0,
                        "current_test_case_title": None,
                        "current_step_info": None,
                        "completed_results": [],
                        "logs": list(logs),
                        "error": "Missing app_url — automation cannot open the application under test.",
                    })
                    self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
                    return

                app_url = app_url_eff

                # Snapshot + stable order: match TestResult insertion order (id ascending)
                ordered_results = sorted(list(run.test_results or []), key=lambda r: r.id)
                total = len(ordered_results)
                tc_ids = [r.test_case_id for r in ordered_results]
                if not tc_ids:
                    _log("✗ No test cases attached to this run.")
                    run.status = TestRunStatus.ERROR
                    run.completed_at = datetime.utcnow()
                    await db.commit()
                    self.progress_manager.set(run_id, {
                        "status": "error",
                        "percentage": 100,
                        "error": "No test cases to execute.",
                        "logs": list(logs),
                        "completed_results": [],
                        "total_test_cases": 0,
                        "current_test_case_index": 0,
                    })
                    self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
                    return

                tc_rows = (await db.execute(
                    select(TestCase)
                    .options(selectinload(TestCase.steps))
                    .where(TestCase.id.in_(tc_ids))
                )).scalars().all()
                tc_map = {tc.id: tc for tc in tc_rows}

                self.progress_manager.set(run_id, {
                    "status": "running",
                    "percentage": 0,
                    "current_test_case_index": 0,
                    "total_test_cases": total,
                    "current_test_case_title": "Initializing…",
                    "current_step_info": None,
                    "completed_results": [],
                    "logs": list(logs),
                    "error": None,
                })

                _log(f"Starting test run with {total} test case(s)")
                _log(f"🔗 Application URL: {app_url}")
                completed_results: List[Dict[str, Any]] = []
                passed = 0
                failed = 0
                runner = TestCaseRunner()
                _log("🚀 Test run started — each case uses its own browser (isolated session)")
                aborted_cancel = False

                for idx, test_result in enumerate(ordered_results):
                        await db.refresh(run)
                        if (
                            run.status == TestRunStatus.CANCELLED
                            or self.progress_manager.is_cancel_requested(run_id)
                        ):
                            await _mark_remaining_skipped(
                                db,
                                ordered_results,
                                idx,
                                tc_map,
                                "Run cancelled by user.",
                                completed_results,
                            )
                            aborted_cancel = True
                            break

                        tc = tc_map.get(test_result.test_case_id)
                        if not tc:
                            _log(f"✗ Test case id={test_result.test_case_id} not found — marking ERROR", test_result.test_case_id)
                            test_result.status = TestResultStatus.ERROR
                            test_result.error_message = "Test case was deleted or is not in this project."
                            test_result.completed_at = datetime.utcnow()
                            await db.commit()
                            failed += 1
                            completed_results.append(
                                completed_case_dict(
                                    test_result_id=test_result.id,
                                    test_case_id=test_result.test_case_id,
                                    title=f"Missing case #{test_result.test_case_id}",
                                    status="error",
                                    steps_total=0,
                                    steps_passed=0,
                                    steps_failed=0,
                                    duration_ms=0,
                                    step_results=[],
                                    adapted_steps=[],
                                    original_steps=[],
                                    agent_logs=None,
                                    screenshot_path=None,
                                )
                            )
                            self.progress_manager.set(run_id, {
                                "status": "running",
                                "percentage": int(((idx + 1) / total) * 100),
                                "current_test_case_index": idx,
                                "total_test_cases": total,
                                "current_test_case_title": None,
                                "current_step_info": None,
                                "completed_results": list(completed_results),
                                "logs": list(logs),
                                "error": None,
                            })
                            continue

                        tc_title = tc.title or f"Test Case #{tc.id}"
                        _log(f"▶ [{idx + 1}/{total}] {tc_title}", tc.id)

                        # Callback to update granular progress during a single test case
                        async def _on_tc_step(step_num: int, desc: str, log_entry: Optional[Dict]):
                            # Calculate granular percentage
                            base_pct = int((idx / total) * 100)
                            tc_pct_contribution = int((1 / total) * 100 * (step_num / 25))
                            total_pct = min(99, base_pct + tc_pct_contribution)
                            
                            self.progress_manager.set(run_id, {
                                "status": "running",
                                "percentage": total_pct,
                                "current_test_case_index": idx,
                                "total_test_cases": total,
                                "current_test_case_title": tc_title,
                                "current_step_info": desc,
                                "completed_results": completed_results,
                                "logs": list(logs),
                                "error": None,
                            })
                            if log_entry:
                                msg = f"  Step {step_num}: {desc}"
                                _log(msg, tc.id)

                        self.progress_manager.set(run_id, {
                            "status": "running",
                            "percentage": int((idx / total) * 100),
                            "current_test_case_index": idx,
                            "total_test_cases": total,
                            "current_test_case_title": tc_title,
                            "current_step_info": "Starting…",
                            "completed_results": completed_results,
                            "logs": list(logs),
                            "error": None,
                        })

                        steps_data = [
                            {
                                "step_number": s.step_number,
                                "action": s.action.value if hasattr(s.action, "value") else str(s.action),
                                "target": s.target,
                                "value": s.value,
                                "description": s.description,
                                "expected_result": s.expected_result,
                            }
                            for s in sorted(tc.steps, key=lambda s: s.step_number)
                        ]

                        if not steps_data:
                            _log(f"✗ {tc_title} — no steps defined; skipping automation", tc.id)
                            test_result.status = TestResultStatus.ERROR
                            test_result.error_message = "Test case has no steps."
                            test_result.duration_ms = 0
                            test_result.completed_at = datetime.utcnow()
                            test_result.step_results = []
                            await db.commit()
                            failed += 1
                            completed_results.append(
                                completed_case_dict(
                                    test_result_id=test_result.id,
                                    test_case_id=tc.id,
                                    title=tc_title,
                                    status="error",
                                    steps_total=0,
                                    steps_passed=0,
                                    steps_failed=0,
                                    duration_ms=0,
                                    step_results=[],
                                    adapted_steps=[],
                                    original_steps=[],
                                    agent_logs=None,
                                    screenshot_path=None,
                                )
                            )
                            continue

                        result = await runner.run(
                            run_id=run_uuid,
                            test_case_id=tc.id,
                            title=tc_title,
                            description=tc.description or "",
                            preconditions=tc.preconditions or "",
                            steps=steps_data,
                            app_url=app_url,
                            username=username,
                            password=password,
                            use_google_signin=use_google_signin,
                            headless=headless,
                            browser_context=None,
                            on_step_callback=_on_tc_step,
                            execution_run_id=run_id,
                        )

                        tc_status = result.get("overall", "error")
                        duration = result.get("duration_ms", 0)
                        
                        # Merge original step info with LLM results
                        final_step_results = []
                        llm_steps = {s.get("step_number"): s for s in result.get("step_results", [])}
                        
                        for s_orig in steps_data:
                            num = s_orig["step_number"]
                            s_res = llm_steps.get(num, {})
                            merged = {
                                **s_orig,
                                "status": s_res.get("status", "skipped"),
                                "actual_result": s_res.get("actual_result"),
                                "adaptation": s_res.get("adaptation"),
                            }
                            final_step_results.append(
                                redact_step_dict(merged, username, password)
                            )

                        safe_agent_logs = redact_agent_logs_list(
                            result.get("logs"), username, password
                        )

                        test_result.status = (
                            TestResultStatus.PASSED if tc_status == "passed"
                            else TestResultStatus.FAILED if tc_status == "failed"
                            else TestResultStatus.SKIPPED if tc_status == "cancelled"
                            else TestResultStatus.ERROR
                        )
                        test_result.duration_ms = duration
                        test_result.started_at = datetime.utcnow()
                        test_result.completed_at = datetime.utcnow()
                        test_result.step_results = final_step_results
                        test_result.adapted_steps = [s for s in final_step_results if s.get("adaptation")]
                        test_result.original_steps = steps_data
                        # First screenshot for legacy consumers; full trail in agent_logs
                        test_result.screenshot_path = (result.get("screenshots") or [None])[0]
                        test_result.agent_logs = safe_agent_logs
                        test_result.error_message = (
                            "Run cancelled by user"
                            if tc_status == "cancelled"
                            else redact_known_credentials(
                                result.get("error"),
                                username=username,
                                password=password,
                            )
                        )
                        test_result.failed_step = next(
                            (s["step_number"] for s in final_step_results if s.get("status") != "passed"),
                            None,
                        )
                        await db.commit()

                        if tc_status == "passed":
                            passed += 1
                            _log(f"✓ {tc_title} — PASSED ({duration}ms)", tc.id)
                        elif tc_status == "cancelled":
                            _log(f"⏹ {tc_title} — CANCELLED ({duration}ms)", tc.id)
                        else:
                            failed += 1
                            _log(f"✗ {tc_title} — {tc_status.upper()} ({duration}ms)", tc.id)

                        completed_results.append(
                            completed_case_dict(
                                test_result_id=test_result.id,
                                test_case_id=tc.id,
                                title=tc_title,
                                status=tc_status,
                                steps_total=result.get("steps_total", 0),
                                steps_passed=result.get("steps_passed", 0),
                                steps_failed=result.get("steps_failed", 0),
                                duration_ms=duration,
                                step_results=final_step_results,
                                adapted_steps=[s for s in final_step_results if s.get("adaptation")],
                                original_steps=steps_data,
                                agent_logs=safe_agent_logs,
                                screenshot_path=test_result.screenshot_path,
                            )
                        )
                        cleanup_tc_progress(f"{run_uuid}:{tc.id}")

                        if tc_status == "cancelled":
                            await _mark_remaining_skipped(
                                db,
                                ordered_results,
                                idx + 1,
                                tc_map,
                                "Run cancelled by user.",
                                completed_results,
                            )
                            aborted_cancel = True
                            break

                if aborted_cancel:
                    skipped_n = sum(
                        1 for r in ordered_results if r.status == TestResultStatus.SKIPPED
                    )
                    run.status = TestRunStatus.CANCELLED
                    run.completed_at = datetime.utcnow()
                    run.passed_tests = passed
                    run.failed_tests = failed
                    run.skipped_tests = skipped_n
                    await db.commit()
                    _log(f"Run cancelled — {passed} passed, {failed} failed, {skipped_n} skipped")
                    self.progress_manager.set(run_id, {
                        "status": "cancelled",
                        "percentage": 100,
                        "current_test_case_index": total,
                        "total_test_cases": total,
                        "current_test_case_title": None,
                        "current_step_info": "Cancelled",
                        "completed_results": completed_results,
                        "logs": list(logs),
                        "error": None,
                    })
                    self.progress_manager.clear_cancel(run_id)
                    self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
                else:
                    run.status = TestRunStatus.PASSED if failed == 0 else TestRunStatus.FAILED
                    run.completed_at = datetime.utcnow()
                    run.passed_tests = passed
                    run.failed_tests = failed
                    await db.commit()

                    _log(f"Run complete — {passed} passed, {failed} failed")
                    self.progress_manager.set(run_id, {
                        "status": "completed",
                        "percentage": 100,
                        "current_test_case_index": total,
                        "total_test_cases": total,
                        "current_test_case_title": None,
                        "current_step_info": "Completed",
                        "completed_results": completed_results,
                        "logs": list(logs),
                        "error": None,
                    })
                    self.progress_manager.clear_cancel(run_id)
                    # Schedule cleanup after 5 minutes
                    self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
            except Exception as e:
                logger.error(f"[TestExecutionService] Fatal error in background execution: {str(e)}")
                _log(f"✗ FATAL ERROR: {str(e)}")
                self.progress_manager.set(run_id, {
                    "status": "error",
                    "percentage": 100,
                    "error": str(e),
                    "logs": list(logs),
                    "completed_results": [],
                })
                # Update DB status if possible
                try:
                    run = (await db.execute(
                        select(TestRun).where(TestRun.id == run_id)
                    )).scalar_one_or_none()
                    if run:
                        run.status = TestRunStatus.ERROR
                        run.completed_at = datetime.utcnow()
                        await db.commit()
                except Exception:
                    pass
                self.progress_manager.clear_cancel(run_id)
                self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)

    async def cancel_run(self, run_id: int) -> Optional[TestRun]:
        self.progress_manager.request_cancel(run_id)
        existing = self.progress_manager.get(run_id) or {}
        self.progress_manager.set(run_id, {
            **existing,
            "status": "cancelling",
            "current_step_info": existing.get("current_step_info") or "Stopping…",
        })
        run = await self.get_run_with_results(run_id)
        if not run:
            return None
        if run.status not in (TestRunStatus.PENDING, TestRunStatus.RUNNING):
            return run
        run.status = TestRunStatus.CANCELLED
        run.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def get_results(self, run_id: int) -> List[TestResult]:
        result = await self.db.execute(
            select(TestResult).where(TestResult.test_run_id == run_id)
        )
        return list(result.scalars().all())

    async def get_result_for_run(self, run_id: int, result_id: int) -> Optional[TestResult]:
        row = await self.db.execute(
            select(TestResult).where(
                TestResult.id == result_id,
                TestResult.test_run_id == run_id,
            )
        )
        return row.scalar_one_or_none()

    async def sync_adapted_step(self, result_id: int, step_number: int) -> bool:
        """Sync an AI-adapted step back to the original test case.
        
        Updates the test step's target/value based on the AI adaptation,
        and also updates the description and expected_result to reflect
        what the AI learned during execution.
        """
        result = await self.db.execute(
            select(TestResult).where(TestResult.id == result_id)
        )
        tr = result.scalar_one_or_none()
        if not tr or not tr.adapted_steps:
            return False
        
        # Find the adapted step
        adapted = next((s for s in tr.adapted_steps if s.get("step_number") == step_number), None)
        if not adapted or not adapted.get("adaptation"):
            return False
            
        # Get the original test step
        from features.functional.db.models.test_step import TestStep
        step_result = await self.db.execute(
            select(TestStep)
            .where(TestStep.test_case_id == tr.test_case_id)
            .where(TestStep.step_number == step_number)
        )
        step = step_result.scalar_one_or_none()
        if not step:
            return False

        adaptation_text = str(adapted.get("adaptation") or "").strip()
        if not adaptation_text:
            return False

        # Also get the actual_result from the step_results for this step
        actual_result_text = ""
        if tr.step_results:
            step_res = next(
                (sr for sr in tr.step_results if sr.get("step_number") == step_number),
                None,
            )
            if step_res:
                actual_result_text = str(step_res.get("actual_result") or "").strip()

        # Support varied LLM phrasings instead of one rigid sentence template.
        quoted = re.findall(r"['\"]([^'\"]{1,200})['\"]", adaptation_text)
        candidate_target = quoted[-1].strip() if quoted else ""

        # Prefer explicit keyword-based extraction when present.
        m = re.search(r"(?:found|use(?:d)?|click(?:ed)?|selector|target)\s+['\"]([^'\"]+)['\"]", adaptation_text, re.IGNORECASE)
        if m:
            candidate_target = m.group(1).strip()

        m_val = re.search(r"(?:value|input|entered|typed)\s+['\"]([^'\"]+)['\"]", adaptation_text, re.IGNORECASE)
        candidate_value = m_val.group(1).strip() if m_val else ""

        action_value = str(getattr(step, "action", "")).lower()
        is_input_action = any(tok in action_value for tok in ("type", "input", "fill"))

        updated = False
        if candidate_value and is_input_action:
            step.value = candidate_value
            updated = True
        elif candidate_target:
            step.target = candidate_target
            updated = True

        # Always update description to include the AI adaptation note
        existing_desc = (step.description or "").strip()
        # Remove any previous sync note to avoid duplicates
        lines = existing_desc.split("\n")
        lines = [l for l in lines if not l.strip().startswith("[Synced adaptation]")]
        clean_desc = "\n".join(lines).strip()
        
        note = f"[Synced adaptation] {adaptation_text}"
        step.description = f"{clean_desc}\n{note}".strip() if clean_desc else note
        updated = True

        # Update expected_result if we have an actual result from execution
        if actual_result_text:
            step.expected_result = actual_result_text

        if updated:
            await self.db.commit()
            return True
        return False

    async def get_primary_screenshot_file(
        self, run_id: int, result_id: int
    ) -> Optional[Path]:
        return await test_result_evidence.get_primary_screenshot_file(
            self.db, run_id, result_id
        )

    async def get_authorized_screenshot_file(
        self, run_id: int, result_id: int, filename: str
    ) -> Optional[Path]:
        return await test_result_evidence.get_authorized_screenshot_file(
            self.db, run_id, result_id, filename
        )
