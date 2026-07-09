"""
Test Execution Service — orchestrates test runs via browser-use.
Runs can execute with one or more workers. Each worker reuses its own browser
session across assigned test cases so login state persists within that worker.
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
from browser_use import Browser, BrowserProfile

from common.api.pagination import PaginationParams
import config
from common.utils.logger import logger
from common.db.models.project import Project
from features.functional.db.models.test_case import TestCase, TestCaseStatus
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.schemas.test_run import TestRunCreate
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args
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
                "max_concurrency": run_data.max_concurrency,
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

        effective_max_concurrency = max(1, int(run_data.max_concurrency or 1))

        # Persist resolved app URL on the run so DB / retries reflect what automation will use
        run_row = (await self.db.execute(select(TestRun).where(TestRun.id == run_id))).scalar_one_or_none()
        if run_row is not None:
            cfg = dict(run_row.config or {})
            if app_url:
                cfg["app_url"] = app_url
            cfg["max_concurrency"] = effective_max_concurrency
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
                    max_concurrency=effective_max_concurrency,
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
                    max_concurrency=effective_max_concurrency,
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
        max_concurrency: int,
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
                result_by_id = {r.id: r for r in ordered_results}

                work_items: List[Dict[str, Any]] = []
                for idx, test_result in enumerate(ordered_results):
                    tc = tc_map.get(test_result.test_case_id)
                    if tc is None:
                        work_items.append({
                            "idx": idx,
                            "test_result_id": test_result.id,
                            "test_case_id": test_result.test_case_id,
                            "title": f"Missing case #{test_result.test_case_id}",
                            "user_story_id": None,
                            "description": "",
                            "preconditions": "",
                            "steps": [],
                            "exists": False,
                        })
                        continue

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
                    work_items.append({
                        "idx": idx,
                        "test_result_id": test_result.id,
                        "test_case_id": tc.id,
                        "title": tc.title or f"Test Case #{tc.id}",
                        "user_story_id": tc.user_story_id,
                        "description": tc.description or "",
                        "preconditions": tc.preconditions or "",
                        "steps": steps_data,
                        "exists": True,
                    })

                story_groups: Dict[str, List[Dict[str, Any]]] = {}
                for item in work_items:
                    group_key = (
                        f"us:{item['user_story_id']}"
                        if item.get("user_story_id") is not None
                        else "us:none"
                    )
                    story_groups.setdefault(group_key, []).append(item)

                effective_workers = max(1, min(max_concurrency, len(story_groups)))
                worker_queues: List[List[Dict[str, Any]]] = [[] for _ in range(effective_workers)]
                worker_loads: List[int] = [0 for _ in range(effective_workers)]

                for group in story_groups.values():
                    least_loaded = min(range(effective_workers), key=lambda i: worker_loads[i])
                    worker_queues[least_loaded].extend(group)
                    worker_loads[least_loaded] += len(group)

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
                _log(f"⚙️ Max concurrency configured: {max_concurrency}")
                _log(f"🧩 User story groups: {len(story_groups)}")
                _log(f"🧵 Worker count in use: {effective_workers}")

                completed_results: List[Dict[str, Any]] = []
                passed = 0
                failed = 0
                completed_count = 0
                executed_result_ids = set()
                state_lock = asyncio.Lock()
                auth_execution_lock = asyncio.Lock()
                runner = TestCaseRunner()

                def _build_browser() -> Browser:
                    return Browser(
                        browser_profile=BrowserProfile(
                            headless=headless,
                            is_local=True,
                            disable_security=True,
                            args=default_browser_chrome_args(),
                            enable_default_extensions=getattr(
                                config, "settings"
                            ).BROWSER_USE_DEFAULT_EXTENSIONS,
                            keep_alive=True,
                        )
                    )

                def _is_auth_sensitive_case(item: Dict[str, Any]) -> bool:
                    # These cases are highly sensitive to pre-existing login state.
                    markers = (
                        "login",
                        "log in",
                        "signin",
                        "sign in",
                        "authentication",
                        "invalid password",
                        "invalid email",
                        "wrong password",
                        "non-existent",
                        "non existent",
                        "unauthorized",
                        "401",
                        "403",
                        "otp",
                        "mfa",
                        "two-factor",
                        "two factor",
                        "forgot password",
                        "reset password",
                    )
                    step_text = " ".join(
                        " ".join(
                            str(s.get(k) or "")
                            for k in ("description", "expected_result", "action", "target", "value")
                        )
                        for s in item.get("steps", [])
                    )
                    haystack = " ".join(
                        [
                            str(item.get("title") or ""),
                            str(item.get("description") or ""),
                            str(item.get("preconditions") or ""),
                            step_text,
                        ]
                    ).lower()
                    return any(marker in haystack for marker in markers)

                async def _publish_running(title: Optional[str], step_info: Optional[str], base_completed: int) -> None:
                    pct = min(99, int((base_completed / total) * 100)) if total else 0
                    self.progress_manager.set(run_id, {
                        "status": "running",
                        "percentage": pct,
                        "current_test_case_index": min(base_completed, total),
                        "total_test_cases": total,
                        "current_test_case_title": title,
                        "current_step_info": step_info,
                        "completed_results": list(completed_results),
                        "logs": list(logs),
                        "error": None,
                    })

                async def _mark_item_complete(item: Dict[str, Any], entry: Dict[str, Any], tc_status: str) -> None:
                    nonlocal passed, failed, completed_count
                    async with state_lock:
                        completed_results.append(entry)
                        executed_result_ids.add(item["test_result_id"])
                        completed_count += 1
                        if tc_status == "passed":
                            passed += 1
                        elif tc_status != "cancelled":
                            failed += 1
                        base_completed = completed_count
                    await _publish_running(None, None, base_completed)

                async def _persist_result(
                    item: Dict[str, Any],
                    worker_id: int,
                    tc_status: str,
                    duration: int,
                    final_step_results: List[Dict[str, Any]],
                    safe_agent_logs: Optional[List[Dict[str, Any]]],
                    screenshot_path: Optional[str],
                    err_msg: Optional[str],
                ) -> None:
                    async with async_session_maker() as wdb:
                        tr_row = (await wdb.execute(
                            select(TestResult).where(TestResult.id == item["test_result_id"])
                        )).scalar_one_or_none()
                        if not tr_row:
                            return
                        tr_row.worker_id = worker_id
                        tr_row.status = (
                            TestResultStatus.PASSED if tc_status == "passed"
                            else TestResultStatus.FAILED if tc_status == "failed"
                            else TestResultStatus.SKIPPED if tc_status == "cancelled"
                            else TestResultStatus.ERROR
                        )
                        tr_row.duration_ms = duration
                        tr_row.started_at = datetime.utcnow()
                        tr_row.completed_at = datetime.utcnow()
                        tr_row.step_results = final_step_results
                        tr_row.adapted_steps = [s for s in final_step_results if s.get("adaptation")]
                        tr_row.original_steps = item["steps"]
                        tr_row.screenshot_path = screenshot_path
                        tr_row.agent_logs = safe_agent_logs
                        tr_row.error_message = err_msg
                        tr_row.failed_step = next(
                            (s["step_number"] for s in final_step_results if s.get("status") != "passed"),
                            None,
                        )
                        await wdb.commit()

                async def _persist_simple_error(item: Dict[str, Any], worker_id: int, err_msg: str) -> None:
                    async with async_session_maker() as wdb:
                        tr_row = (await wdb.execute(
                            select(TestResult).where(TestResult.id == item["test_result_id"])
                        )).scalar_one_or_none()
                        if not tr_row:
                            return
                        tr_row.worker_id = worker_id
                        tr_row.status = TestResultStatus.ERROR
                        tr_row.error_message = err_msg
                        tr_row.duration_ms = 0
                        tr_row.completed_at = datetime.utcnow()
                        tr_row.step_results = []
                        tr_row.failed_step = None
                        await wdb.commit()

                def _screenshot_belongs_to_testcase(path: Optional[str], tc_id: int) -> bool:
                    if not path or not isinstance(path, str):
                        return False
                    return re.search(rf"_tc{int(tc_id)}_", path) is not None

                def _sanitize_evidence_for_testcase(
                    tc_id: int,
                    screenshots: List[Any],
                    logs_list: Optional[List[Dict[str, Any]]],
                ) -> Tuple[List[str], Optional[List[Dict[str, Any]]], int, int]:
                    valid_screenshots: List[str] = []
                    dropped_screenshot_count = 0
                    for raw in screenshots or []:
                        path = str(raw) if raw is not None else ""
                        if _screenshot_belongs_to_testcase(path, tc_id):
                            valid_screenshots.append(path)
                        elif path:
                            dropped_screenshot_count += 1
                            _log(
                                f"⚠ Dropped screenshot that does not belong to tc={tc_id}: {path}",
                                tc_id,
                            )

                    if not logs_list:
                        return valid_screenshots, logs_list, dropped_screenshot_count, 0

                    cleaned_logs: List[Dict[str, Any]] = []
                    dropped_log_screenshot_count = 0
                    for entry in logs_list:
                        log_entry = dict(entry or {})
                        sp = log_entry.get("screenshot_path")
                        if sp and not _screenshot_belongs_to_testcase(str(sp), tc_id):
                            dropped_log_screenshot_count += 1
                            _log(
                                f"⚠ Dropped agent log screenshot mismatch for tc={tc_id}: {sp}",
                                tc_id,
                            )
                            log_entry["screenshot_path"] = None
                        cleaned_logs.append(log_entry)
                    return (
                        valid_screenshots,
                        cleaned_logs,
                        dropped_screenshot_count,
                        dropped_log_screenshot_count,
                    )

                async def _worker(worker_id: int, queue: List[Dict[str, Any]]) -> None:
                    worker_browser = _build_browser()
                    _log(f"🧵 Worker {worker_id} started ({len(queue)} case(s))")
                    try:
                        for item in queue:
                            if self.progress_manager.is_cancel_requested(run_id):
                                break

                            tc_title = item["title"]
                            tc_id = item["test_case_id"]

                            async with state_lock:
                                base_completed = completed_count
                            await _publish_running(tc_title, f"Worker {worker_id}: Starting…", base_completed)

                            isolated_browser: Optional[Browser] = None
                            try:
                                if not item["exists"]:
                                    _log(
                                        f"✗ [W{worker_id}] Test case id={tc_id} not found — marking ERROR",
                                        tc_id,
                                    )
                                    await _persist_simple_error(item, worker_id, "Test case was deleted or is not in this project.")
                                    entry = completed_case_dict(
                                        test_result_id=item["test_result_id"],
                                        test_case_id=tc_id,
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
                                    await _mark_item_complete(item, entry, "error")
                                    continue

                                if not item["steps"]:
                                    _log(f"✗ [W{worker_id}] {tc_title} — no steps defined; skipping automation", tc_id)
                                    await _persist_simple_error(item, worker_id, "Test case has no steps.")
                                    entry = completed_case_dict(
                                        test_result_id=item["test_result_id"],
                                        test_case_id=tc_id,
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
                                    await _mark_item_complete(item, entry, "error")
                                    continue

                                _log(f"▶ [W{worker_id}] {tc_title}", tc_id)

                                case_browser: Browser = worker_browser
                                is_auth_sensitive = _is_auth_sensitive_case(item)
                                if is_auth_sensitive:
                                    isolated_browser = _build_browser()
                                    case_browser = isolated_browser
                                    _log(
                                        f"🔐 [W{worker_id}] Auth-sensitive case uses isolated browser session",
                                        tc_id,
                                    )

                                async def _on_tc_step(step_num: int, desc: str, log_entry: Optional[Dict]):
                                    async with state_lock:
                                        base = completed_count
                                    base_pct = min(99, int((base / total) * 100)) if total else 0
                                    tc_pct_contribution = int((1 / max(total, 1)) * 100 * (step_num / 25))
                                    total_pct = min(99, base_pct + tc_pct_contribution)
                                    self.progress_manager.set(run_id, {
                                        "status": "running",
                                        "percentage": total_pct,
                                        "current_test_case_index": min(base, total),
                                        "total_test_cases": total,
                                        "current_test_case_title": tc_title,
                                        "current_step_info": f"Worker {worker_id}: {desc}",
                                        "completed_results": list(completed_results),
                                        "logs": list(logs),
                                        "error": None,
                                    })
                                    if log_entry:
                                        _log(f"  [W{worker_id}] Step {step_num}: {desc}", tc_id)

                                async def _run_current_case() -> Dict[str, Any]:
                                    return await runner.run(
                                        run_id=run_uuid,
                                        test_case_id=tc_id,
                                        title=tc_title,
                                        description=item["description"],
                                        preconditions=item["preconditions"],
                                        steps=item["steps"],
                                        app_url=app_url,
                                        username=username,
                                        password=password,
                                        use_google_signin=use_google_signin,
                                        headless=headless,
                                        capture_screenshots=True,
                                        browser_context=case_browser,
                                        on_step_callback=_on_tc_step,
                                        execution_run_id=run_id,
                                    )

                                if is_auth_sensitive:
                                    _log(
                                        f"🔒 [W{worker_id}] Auth-sensitive execution lock acquired",
                                        tc_id,
                                    )
                                    async with auth_execution_lock:
                                        result = await _run_current_case()
                                else:
                                    result = await _run_current_case()

                                tc_status = result.get("overall", "error")
                                duration = result.get("duration_ms", 0)

                                llm_steps = {
                                    s.get("step_number"): s
                                    for s in result.get("step_results", [])
                                }
                                final_step_results: List[Dict[str, Any]] = []
                                for s_orig in item["steps"]:
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
                                screenshots_raw = result.get("screenshots") or []
                                (
                                    safe_screenshots,
                                    safe_agent_logs,
                                    dropped_screenshots_count,
                                    dropped_log_screenshot_count,
                                ) = _sanitize_evidence_for_testcase(
                                    tc_id=tc_id,
                                    screenshots=screenshots_raw,
                                    logs_list=safe_agent_logs,
                                )
                                if safe_agent_logs is None:
                                    safe_agent_logs = []
                                safe_agent_logs.insert(0, {
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "agent_step": 0,
                                    "description": "[debug] Worker assignment metadata",
                                    "adaptation": None,
                                    "screenshot_path": None,
                                    "debug": {
                                        "worker_id": worker_id,
                                        "run_uuid": run_uuid,
                                        "test_case_id": tc_id,
                                        "test_result_id": item["test_result_id"],
                                        "user_story_id": item.get("user_story_id"),
                                        "auth_sensitive_case": is_auth_sensitive,
                                        "isolated_browser": bool(isolated_browser is not None),
                                        "dropped_screenshot_count": dropped_screenshots_count,
                                        "dropped_agentlog_screenshot_count": dropped_log_screenshot_count,
                                    },
                                })
                                screenshot_path = (safe_screenshots or [None])[0]
                                err_msg = (
                                    "Run cancelled by user"
                                    if tc_status == "cancelled"
                                    else redact_known_credentials(
                                        result.get("error"),
                                        username=username,
                                        password=password,
                                    )
                                )

                                await _persist_result(
                                    item,
                                    worker_id=worker_id,
                                    tc_status=tc_status,
                                    duration=duration,
                                    final_step_results=final_step_results,
                                    safe_agent_logs=safe_agent_logs,
                                    screenshot_path=screenshot_path,
                                    err_msg=err_msg,
                                )

                                entry = completed_case_dict(
                                    test_result_id=item["test_result_id"],
                                    test_case_id=tc_id,
                                    title=tc_title,
                                    status=tc_status,
                                    steps_total=result.get("steps_total", 0),
                                    steps_passed=result.get("steps_passed", 0),
                                    steps_failed=result.get("steps_failed", 0),
                                    duration_ms=duration,
                                    step_results=final_step_results,
                                    adapted_steps=[s for s in final_step_results if s.get("adaptation")],
                                    original_steps=item["steps"],
                                    agent_logs=safe_agent_logs,
                                    screenshot_path=screenshot_path,
                                )
                                await _mark_item_complete(item, entry, tc_status)

                                if tc_status == "passed":
                                    _log(f"✓ [W{worker_id}] {tc_title} — PASSED ({duration}ms)", tc_id)
                                elif tc_status == "cancelled":
                                    _log(f"⏹ [W{worker_id}] {tc_title} — CANCELLED ({duration}ms)", tc_id)
                                    self.progress_manager.request_cancel(run_id)
                                    break
                                else:
                                    _log(f"✗ [W{worker_id}] {tc_title} — {tc_status.upper()} ({duration}ms)", tc_id)

                                cleanup_tc_progress(f"{run_uuid}:{tc_id}")
                                if isolated_browser is not None:
                                    try:
                                        await isolated_browser.kill()
                                    except Exception as isolated_browser_cleanup_error:
                                        logger.warning(
                                            f"[TestExecutionService] Worker {worker_id} isolated browser cleanup failed: {isolated_browser_cleanup_error}"
                                        )
                            except Exception as tc_exc:
                                safe_err = redact_known_credentials(
                                    str(tc_exc), username=username, password=password
                                )
                                safe_err_str = safe_err or "Worker execution error"
                                _log(f"✗ [W{worker_id}] {tc_title} — ERROR ({safe_err_str})", tc_id)
                                await _persist_simple_error(item, worker_id, safe_err_str)
                                entry = completed_case_dict(
                                    test_result_id=item["test_result_id"],
                                    test_case_id=tc_id,
                                    title=tc_title,
                                    status="error",
                                    steps_total=0,
                                    steps_passed=0,
                                    steps_failed=0,
                                    duration_ms=0,
                                    step_results=[],
                                    adapted_steps=[],
                                    original_steps=item["steps"],
                                    agent_logs=None,
                                    screenshot_path=None,
                                )
                                await _mark_item_complete(item, entry, "error")
                                if isolated_browser is not None:
                                    try:
                                        await isolated_browser.kill()
                                    except Exception as isolated_browser_cleanup_error:
                                        logger.warning(
                                            f"[TestExecutionService] Worker {worker_id} isolated browser cleanup failed: {isolated_browser_cleanup_error}"
                                        )
                    finally:
                        try:
                            await worker_browser.kill()
                        except Exception as browser_cleanup_error:
                            logger.warning(
                                f"[TestExecutionService] Worker {worker_id} browser cleanup failed: {browser_cleanup_error}"
                            )

                await asyncio.gather(
                    *[
                        _worker(worker_id=i + 1, queue=q)
                        for i, q in enumerate(worker_queues)
                        if q
                    ]
                )

                cancelled = self.progress_manager.is_cancel_requested(run_id)
                if cancelled:
                    cancel_reason = "Run cancelled by user."
                    for item in work_items:
                        tr_id = item["test_result_id"]
                        if tr_id in executed_result_ids:
                            continue
                        tr_row = result_by_id.get(tr_id)
                        if tr_row:
                            tr_row.status = TestResultStatus.SKIPPED
                            tr_row.error_message = cancel_reason
                            tr_row.completed_at = datetime.utcnow()
                            tr_row.duration_ms = tr_row.duration_ms or 0
                            tr_row.step_results = []
                            tr_row.failed_step = None
                        completed_results.append(
                            completed_case_dict(
                                test_result_id=tr_id,
                                test_case_id=item["test_case_id"],
                                title=item["title"],
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

                status_rows = (await db.execute(
                    select(TestResult.status, func.count(TestResult.id))
                    .where(TestResult.test_run_id == run_id)
                    .group_by(TestResult.status)
                )).all()
                passed_n = 0
                failed_n = 0
                skipped_n = 0
                for st, cnt in status_rows:
                    n = int(cnt or 0)
                    if st == TestResultStatus.PASSED:
                        passed_n += n
                    elif st in (TestResultStatus.FAILED, TestResultStatus.ERROR):
                        failed_n += n
                    elif st == TestResultStatus.SKIPPED:
                        skipped_n += n

                run.status = TestRunStatus.CANCELLED if cancelled else (
                    TestRunStatus.PASSED if failed_n == 0 else TestRunStatus.FAILED
                )
                run.completed_at = datetime.utcnow()
                run.passed_tests = passed_n
                run.failed_tests = failed_n
                run.skipped_tests = skipped_n
                await db.commit()

                if cancelled:
                    _log(f"Run cancelled — {passed_n} passed, {failed_n} failed, {skipped_n} skipped")
                    final_status = "cancelled"
                    final_step = "Cancelled"
                else:
                    _log(f"Run complete — {passed_n} passed, {failed_n} failed")
                    final_status = "completed"
                    final_step = "Completed"

                self.progress_manager.set(run_id, {
                    "status": final_status,
                    "percentage": 100,
                    "current_test_case_index": total,
                    "total_test_cases": total,
                    "current_test_case_title": None,
                    "current_step_info": final_step,
                    "completed_results": completed_results,
                    "logs": list(logs),
                    "error": None,
                })
                self.progress_manager.clear_cancel(run_id)
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
