"""
Test Execution Service — orchestrates test run lifecycle.
Runs test cases sequentially, one at a time, using TestCaseRunner.
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
from features.functional.db.models.test_case import TestCase, TestCaseStatus
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.schemas.test_run import TestRunCreate
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.services.completed_result_builder import completed_case_dict
from features.functional.services.test_run_stats import fetch_test_run_summary
from features.functional.services import test_result_evidence

# India Standard Time (no DST); avoids tzdata/zoneinfo issues on minimal Windows installs.
_IST = timezone(timedelta(hours=5, minutes=30))



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
            missing = [i for i in run_data.test_case_ids if i not in by_id]
            if missing:
                raise ValueError(
                    "One or more test cases were not found in this project."
                )
            # Preserve client order (SQL IN does not guarantee order)
            test_cases = [by_id[i] for i in run_data.test_case_ids]
            not_ready = [tc for tc in test_cases if tc.status != TestCaseStatus.ready]
            if not_ready:
                raise ValueError(
                    "Only test cases with status 'ready' can be executed. "
                    f"{len(not_ready)} selected case(s) are draft or deprecated."
                )
        else:
            tc_result = await self.db.execute(
                select(TestCase)
                .where(TestCase.project_id == run_data.project_id)
                .where(TestCase.status == TestCaseStatus.ready)
                .order_by(TestCase.id)
            )
            test_cases = list(tc_result.scalars().all())
            if not test_cases:
                raise ValueError(
                    "No runnable test cases: mark at least one case as Ready "
                    "before starting a run."
                )

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
        
        final_creds = {"username": username, "password": password}
        execution_strategy = (run_data.execution_strategy or "sequential").strip().lower()

        # Persist resolved app URL + strategy on the run
        run_row = (await self.db.execute(select(TestRun).where(TestRun.id == run_id))).scalar_one_or_none()
        if run_row is not None:
            cfg = dict(run_row.config or {})
            if app_url:
                cfg["app_url"] = app_url
            cfg["execution_strategy"] = execution_strategy
            run_row.config = cfg
            await self.db.commit()

        bg_kwargs = dict(
            run_id=run_id,
            app_url=app_url,
            username=final_creds["username"],
            password=final_creds["password"],
            use_google_signin=run_data.use_google_signin,
            headless=run_data.headless,
            execution_strategy=execution_strategy,
        )

        if sys.platform == "win32":
            # On Windows, we must run the background execution in a separate thread
            # with a ProactorEventLoop to support subprocesses (browser-use launches Chrome).
            asyncio.create_task(
                asyncio.to_thread(self._run_background_sync, **bg_kwargs)
            )
        else:
            asyncio.create_task(self._execute_background(**bg_kwargs))

    def _run_background_sync(self, **kwargs: Any) -> None:
        """Synchronous wrapper to run the background task in a new event loop on Windows."""
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        loop = policy.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute_background(**kwargs))
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
        execution_strategy: str = "sequential",
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

                from features.functional.core.browser.test_case_runner import TestCaseRunner
                from features.functional.utils.credentials_redaction import (
                    redact_agent_logs_list,
                    redact_step_dict,
                )

                runner = TestCaseRunner()
                completed_results: List[Dict[str, Any]] = []
                passed_count = 0
                failed_count = 0

                for idx, result in enumerate(ordered_results):
                    if self.progress_manager.is_cancel_requested(run_id):
                        _log("Run cancelled by user.")
                        break

                    tc = tc_map.get(result.test_case_id)
                    if not tc:
                        _log(f"✗ Test case {result.test_case_id} not found — skipping.", result.test_case_id)
                        continue

                    tc_title = tc.title or f"Test Case #{tc.id}"
                    _log(f"▶ [{idx + 1}/{total}]: {tc_title}", tc.id)

                    pct_start = int((idx / total) * 100) if total > 0 else 0
                    self.progress_manager.set(run_id, {
                        "status": "running",
                        "percentage": pct_start,
                        "current_test_case_index": idx,
                        "total_test_cases": total,
                        "current_test_case_title": tc_title,
                        "current_step_info": f"Running {tc_title}…",
                        "completed_results": list(completed_results),
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
                        for s in sorted(tc.steps, key=lambda x: x.step_number)
                    ]

                    result.started_at = datetime.utcnow()
                    await db.commit()

                    tc_outcome = await runner.run(
                        run_id=str(run_id),
                        test_case_id=tc.id,
                        title=tc.title or "",
                        description=tc.description or "",
                        preconditions=tc.preconditions or "",
                        steps=steps_data,
                        app_url=app_url,
                        username=username,
                        password=password,
                        use_google_signin=use_google_signin,
                        headless=headless,
                        execution_run_id=run_id,
                    )

                    if tc_outcome.get("status") == "cancelled":
                        _log(f"✗ Run cancelled during: {tc_title}", tc.id)
                        result.status = TestResultStatus.SKIPPED
                        result.completed_at = datetime.utcnow()
                        await db.commit()
                        break

                    outcome_overall = tc_outcome.get("overall", "failed")
                    if outcome_overall == "passed":
                        result_status = TestResultStatus.PASSED
                        passed_count += 1
                    elif outcome_overall == "error":
                        result_status = TestResultStatus.ERROR
                        failed_count += 1
                    else:
                        result_status = TestResultStatus.FAILED
                        failed_count += 1

                    step_results = tc_outcome.get("step_results") or []
                    agent_logs_raw = tc_outcome.get("logs") or []
                    redacted_logs = redact_agent_logs_list(agent_logs_raw, username=username, password=password)
                    redacted_steps = [redact_step_dict(s, username=username, password=password) for s in step_results]
                    adapted_steps = [s for s in redacted_steps if s.get("adaptation")]
                    first_screenshot = (tc_outcome.get("screenshots") or [None])[0]
                    failed_step = next(
                        (s.get("step_number") for s in step_results if s.get("status") != "passed"), None
                    )

                    result.status = result_status
                    result.duration_ms = tc_outcome.get("duration_ms")
                    result.step_results = redacted_steps or None
                    result.adapted_steps = adapted_steps or None
                    result.original_steps = steps_data
                    result.agent_logs = redacted_logs or None
                    result.screenshot_path = first_screenshot
                    result.failed_step = failed_step
                    result.error_message = tc_outcome.get("error") or (
                        tc_outcome.get("summary") if outcome_overall != "passed" else None
                    )
                    result.completed_at = datetime.utcnow()
                    await db.commit()

                    _log(
                        f"{'✓' if outcome_overall == 'passed' else '✗'} [{idx + 1}/{total}] {tc_title}: {outcome_overall.upper()}",
                        tc.id,
                    )

                    completed_results.append(completed_case_dict(
                        test_result_id=result.id,
                        test_case_id=tc.id,
                        title=tc_title,
                        status=result_status.value,
                        steps_total=tc_outcome.get("steps_total", len(steps_data)),
                        steps_passed=tc_outcome.get("steps_passed", 0),
                        steps_failed=tc_outcome.get("steps_failed", 0),
                        duration_ms=tc_outcome.get("duration_ms") or 0,
                        step_results=redacted_steps or None,
                        adapted_steps=adapted_steps or None,
                        original_steps=steps_data,
                        agent_logs=redacted_logs or None,
                        screenshot_path=first_screenshot,
                    ))

                    pct_done = int(((idx + 1) / total) * 100) if total > 0 else 100
                    self.progress_manager.set(run_id, {
                        "status": "running",
                        "percentage": pct_done,
                        "current_test_case_index": idx + 1,
                        "total_test_cases": total,
                        "current_test_case_title": tc_title,
                        "current_step_info": None,
                        "completed_results": list(completed_results),
                        "logs": list(logs),
                        "error": None,
                    })

                # ── Finalize run ───────────────────────────────────────────────
                was_cancelled = self.progress_manager.is_cancel_requested(run_id)
                if was_cancelled:
                    final_status = TestRunStatus.CANCELLED
                elif failed_count > 0:
                    final_status = TestRunStatus.FAILED
                elif passed_count > 0:
                    final_status = TestRunStatus.PASSED
                else:
                    final_status = TestRunStatus.ERROR

                run.status = final_status
                run.passed_tests = passed_count
                run.failed_tests = failed_count
                run.completed_at = datetime.utcnow()
                await db.commit()

                _log(f"Run complete — {passed_count} passed, {failed_count} failed")

                self.progress_manager.set(run_id, {
                    "status": "cancelled" if was_cancelled else "completed",
                    "percentage": 100,
                    "current_test_case_index": total,
                    "total_test_cases": total,
                    "current_test_case_title": None,
                    "current_step_info": None,
                    "completed_results": list(completed_results),
                    "logs": list(logs),
                    "error": None,
                })
                self.progress_manager.clear_cancel(run_id)
                self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
                return
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
