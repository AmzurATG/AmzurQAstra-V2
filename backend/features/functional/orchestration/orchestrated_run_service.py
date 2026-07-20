"""Orchestrated run-all service (LangGraph + 6 local browser lanes)."""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.db.database import async_session_maker
from common.db.models.project import Project
from common.utils.logger import logger
import config
from features.functional.db.models.test_case import TestCase, TestCaseStatus
from features.functional.db.models.test_result import TestResult, TestResultStatus
from features.functional.db.models.test_run import TestRun, TestRunStatus
from features.functional.db.models.test_run_group import TestRunGroup, TestRunGroupStatus
from features.functional.orchestration.graph import compile_orchestration_graph
from features.functional.orchestration.state import CasePayload, OrchestrationState
from features.functional.schemas.test_run import TestRunCreate, TestRunCredentials
from features.functional.services.run_progress_manager import RunProgressManager
from features.functional.services.test_execution_service import TestExecutionService


class OrchestratedRunService:
    """Entry point for CSV -> Run All orchestrated execution."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.progress_manager = RunProgressManager()

    async def _load_case_payloads(
        self, project_id: int, test_case_ids: Optional[List[int]] = None
    ) -> List[CasePayload]:
        # Run All executes every non-deprecated case in the project (drafts too);
        # drafts are promoted to ready in create_run_all so they actually run.
        q = (
            select(TestCase)
            .where(TestCase.project_id == project_id)
            .where(TestCase.status != TestCaseStatus.deprecated)
            .options(selectinload(TestCase.steps))
            .order_by(TestCase.id)
        )
        if test_case_ids:
            q = q.where(TestCase.id.in_(test_case_ids))
        rows = list((await self.db.execute(q)).scalars().all())
        if not rows:
            raise ValueError(
                "No test cases to run. Upload a CSV or create cases first."
            )
        payloads: List[CasePayload] = []
        for tc in rows:
            steps_data = [
                {
                    "step_number": s.step_number,
                    "action": s.action.value if hasattr(s.action, "value") else str(s.action),
                    "target": s.target,
                    "value": s.value,
                    "description": s.description,
                    "expected_result": s.expected_result,
                }
                for s in sorted(tc.steps or [], key=lambda x: x.step_number)
            ]
            payloads.append(
                CasePayload(
                    test_case_id=tc.id,
                    test_result_id=0,
                    title=tc.title,
                    description=tc.description or "",
                    preconditions=tc.preconditions or "",
                    steps=steps_data,
                    user_story_id=tc.user_story_id,
                )
            )
        return payloads

    async def create_run_all(
        self,
        *,
        project_id: int,
        triggered_by: int,
        app_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_google_signin: bool = False,
        headless: bool = False,
        test_case_ids: Optional[List[int]] = None,
        mark_ready_on_import: bool = False,
    ) -> TestRun:
        payloads = await self._load_case_payloads(project_id, test_case_ids)

        # Promote any non-ready target cases to ready so Run All truly runs
        # everything (imported CSV cases land as draft otherwise).
        target_ids = [p["test_case_id"] for p in payloads]
        from sqlalchemy import update as _sql_update

        await self.db.execute(
            _sql_update(TestCase)
            .where(TestCase.id.in_(target_ids))
            .where(TestCase.status != TestCaseStatus.ready)
            .values(status=TestCaseStatus.ready)
        )
        await self.db.commit()

        proj = (
            await self.db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        resolved_url = (app_url or "").strip() or None
        if proj:
            if not resolved_url and proj.app_url:
                resolved_url = (proj.app_url or "").strip() or None
            creds = proj.app_credentials or {}
            if not username:
                username = creds.get("username")
            if not password:
                password = creds.get("password")

        lane_count = int(getattr(config.settings, "ORCHESTRATION_LANE_COUNT", 6) or 6)
        exec_svc = TestExecutionService(self.db)
        run_data = TestRunCreate(
            project_id=project_id,
            name=f"Run All {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
            test_case_ids=[p["test_case_id"] for p in payloads],
            app_url=resolved_url,
            credentials=TestRunCredentials(username=username, password=password)
            if username and password
            else None,
            use_google_signin=use_google_signin,
            headless=headless,
            max_concurrency=lane_count,
            config={"orchestration": "langgraph", "lane_count": lane_count},
        )
        run = await exec_svc.create_run(run_data, triggered_by=triggered_by)
        # Attach test_result_id to each payload
        tr_rows = (
            await self.db.execute(
                select(TestResult).where(TestResult.test_run_id == run.id)
            )
        ).scalars().all()
        tr_by_case = {tr.test_case_id: tr.id for tr in tr_rows}
        for p in payloads:
            p["test_result_id"] = tr_by_case.get(int(p["test_case_id"]), 0)
        run.config = {
            **(run.config or {}),
            "orchestration": "langgraph",
            "lane_count": lane_count,
            "case_payloads": payloads,
            "app_url": resolved_url,
            "run_uuid": str(uuid.uuid4()),
        }
        await self.db.commit()
        await self.db.refresh(run)
        return run

    @staticmethod
    def _llm_preflight() -> Optional[str]:
        """Verify the browser LLM is usable before running. Returns an error string if not.

        Catches proxy budget/quota/auth/connection problems up front so a run does
        not burn through hundreds of cases that would all fail identically.
        """
        try:
            from features.functional.core.browser.browser_use_llm import get_browser_use_llm  # noqa: F401
            from openai import OpenAI

            base = (config.settings.LITELLM_API_BASE or "").strip()
            key = (config.settings.LITELLM_API_KEY or "").strip()
            backend = (config.settings.BROWSER_USE_LLM_BACKEND or "litellm").strip().lower()
            if backend != "litellm" or not base or not key:
                return None  # non-proxy backend; skip preflight
            model = (config.settings.BROWSER_USE_LLM_MODEL or config.settings.LITELLM_MODEL).strip()
            client = OpenAI(api_key=key, base_url=base.rstrip("/"))
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=3,
            )
            return None
        except Exception as exc:
            msg = str(exc)
            low = msg.lower()
            if "budget" in low and "exceed" in low:
                return (
                    "LLM budget exceeded on the proxy. Increase the team's max budget "
                    "or use a different LITELLM_API_KEY before running. (Proxy: "
                    f"{config.settings.LITELLM_API_BASE})"
                )
            if "rate" in low and "limit" in low:
                return "LLM rate limit hit on the proxy. Wait and retry, or lower ORCHESTRATION_LANE_COUNT."
            if "401" in low or "403" in low or "unauthor" in low or "api key" in low:
                return "LLM auth failed. Check LITELLM_API_KEY."
            return f"LLM preflight failed: {msg[:300]}"

    async def start_orchestrated_run(self, run_id: int) -> None:
        run = (
            await self.db.execute(select(TestRun).where(TestRun.id == run_id))
        ).scalar_one_or_none()
        if not run:
            raise ValueError(f"Run {run_id} not found")
        cfg = dict(run.config or {})
        payloads = cfg.get("case_payloads") or []
        if not payloads:
            raise ValueError("Run missing orchestration case payloads")

        # Preflight: confirm the LLM is usable before executing anything.
        preflight_error = await asyncio.to_thread(self._llm_preflight)
        if preflight_error:
            logger.error("[OrchestratedRun] run_id=%s preflight failed: %s", run_id, preflight_error)
            run.status = TestRunStatus.ERROR
            run.completed_at = datetime.utcnow()
            await self.db.commit()
            self.progress_manager.set(
                run_id,
                {
                    "status": "error",
                    "percentage": 0,
                    "total_test_cases": len(payloads),
                    "error": preflight_error,
                    "current_step_info": preflight_error,
                    "completed_results": [],
                    "logs": [],
                    "active_lanes": [],
                    "groups": [],
                },
            )
            self.progress_manager.schedule_cleanup(run_id, delay_seconds=300)
            return

        app_url = cfg.get("app_url")
        creds_username = None
        creds_password = None
        if cfg.get("has_credentials"):
            proj = (
                await self.db.execute(select(Project).where(Project.id == run.project_id))
            ).scalar_one_or_none()
            if proj and proj.app_credentials:
                creds_username = proj.app_credentials.get("username")
                creds_password = proj.app_credentials.get("password")

        run.status = TestRunStatus.RUNNING
        run.started_at = datetime.utcnow()
        await self.db.commit()

        initial_state: OrchestrationState = {
            "run_id": run_id,
            "run_uuid": str(uuid.uuid4()),
            "project_id": run.project_id,
            "app_url": app_url or "",
            "username": creds_username,
            "password": creds_password,
            "use_google_signin": bool(cfg.get("use_google_signin")),
            "headless": str(run.headless).lower() == "true",
            "cases": payloads,
            "total_cases": len(payloads),
            "lane_count": int(cfg.get("lane_count") or 6),
            "status": "starting",
        }

        self.progress_manager.set(
            run_id,
            {
                "status": "running",
                "percentage": 0,
                "current_test_case_index": 0,
                "total_test_cases": len(payloads),
                "current_test_case_title": "Planning execution groups…",
                "current_step_info": "LangGraph orchestrator",
                "completed_results": [],
                "logs": [],
                "active_lanes": [],
                "groups": [],
                "live_screenshots": [],
            },
        )

        if sys.platform == "win32":
            asyncio.create_task(
                asyncio.to_thread(self._run_graph_sync, run_id, initial_state)
            )
        else:
            asyncio.create_task(self._run_graph_async(run_id, initial_state))

    def _run_graph_sync(self, run_id: int, state: OrchestrationState) -> None:
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        loop = policy.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_graph_async(run_id, state))
        finally:
            loop.close()

    async def _run_graph_async(self, run_id: int, state: OrchestrationState) -> None:
        try:
            graph = await compile_orchestration_graph(async_session_maker)
            config_dict = {"configurable": {"thread_id": f"run-{run_id}"}}
            await graph.ainvoke(state, config=config_dict)
        except Exception as exc:
            logger.exception("[OrchestratedRun] run_id=%s failed: %s", run_id, exc)
            self.progress_manager.set(
                run_id,
                {
                    "status": "error",
                    "error": str(exc),
                    "percentage": 0,
                },
            )
            async with async_session_maker() as db:
                run = (
                    await db.execute(select(TestRun).where(TestRun.id == run_id))
                ).scalar_one_or_none()
                if run:
                    run.status = TestRunStatus.ERROR
                    run.completed_at = datetime.utcnow()
                    await db.commit()

    async def persist_group_table(self, run_id: int, groups: List[Dict[str, Any]]) -> None:
        for g in groups:
            self.db.add(
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
        await self.db.commit()

    async def cancel_run(self, run_id: int) -> Optional[TestRun]:
        self.progress_manager.request_cancel(run_id)
        existing = self.progress_manager.get(run_id) or {}
        self.progress_manager.update(
            run_id,
            {
                "status": "cancelling",
                "current_step_info": "Cancelling orchestrated run…",
                "active_lanes": existing.get("active_lanes") or [],
            },
        )
        run = (
            await self.db.execute(select(TestRun).where(TestRun.id == run_id))
        ).scalar_one_or_none()
        if not run:
            return None
        cfg = dict(run.config or {})
        cfg["cancel_requested"] = True
        run.config = cfg
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def resume_run(self, run_id: int) -> None:
        """Resume an orchestrated run from LangGraph Postgres checkpoint (same thread_id)."""
        run = (
            await self.db.execute(select(TestRun).where(TestRun.id == run_id))
        ).scalar_one_or_none()
        if not run:
            raise ValueError("Run not found")
        run.status = TestRunStatus.RUNNING
        await self.db.commit()

        graph = await compile_orchestration_graph(async_session_maker)
        config_dict = {"configurable": {"thread_id": f"run-{run_id}"}}
        try:
            snapshot = await graph.aget_state(config_dict)
            if snapshot and snapshot.next:
                await graph.ainvoke(None, config=config_dict)
                return
        except Exception as exc:
            logger.warning("[OrchestratedRun] Checkpoint resume failed, cold restart: %s", exc)

        cfg = dict(run.config or {})
        payloads = cfg.get("case_payloads") or []
        state: OrchestrationState = {
            "run_id": run_id,
            "run_uuid": cfg.get("run_uuid") or str(uuid.uuid4()),
            "project_id": run.project_id,
            "app_url": cfg.get("app_url") or "",
            "cases": payloads,
            "total_cases": len(payloads),
            "lane_count": int(cfg.get("lane_count") or 6),
            "status": "resuming",
        }
        await self._run_graph_async(run_id, state)
