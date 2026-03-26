"""
Integrity Check Service

Orchestrates a full integrity check run:
1. Navigate to the app URL (verify reachability)
2. Login with saved or inline credentials (app form or in-page Google SSO per ``login_mode``)
3. Execute each flagged test case step-by-step
4. Capture a screenshot after every step
5. Call the LLM to diagnose failures (network log + optional screenshot vision)
6. Persist the full run + step results to the database
7. Return the structured response for the API
"""
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from config import settings
from common.utils.logger import logger
from common.llm.factory import get_llm_client
from common.llm.base import Message
from common.llm.litellm_client import LiteLLMClient
from common.db.models.integrity_check_run import IntegrityCheckRun
from common.services.auth_session_service import AuthSessionService
from features.functional.core.browser.factory import get_browser_runner
from features.functional.core.browser.browser_engine_policy import (
    effective_browser_label,
    require_steel_key_if_steel_engine,
    resolve_runner_engine,
    steel_cdp_enabled_for_engine,
)
from features.functional.core.browser.base import BrowserRunner
from features.functional.core.browser.action_dispatcher import dispatch as dispatch_action
from features.functional.core.llm_prompts.integrity_diagnosis import (
    build_failure_diagnosis_prompt,
    build_login_failure_diagnosis_prompt,
)
from features.functional.core.captcha_detection import detect_captcha_signals
from features.functional.services.login_service import LoginService, LoginResult
from features.functional.services.integrity_check_repository import IntegrityCheckRepository
from features.functional.schemas.integrity_check import (
    IntegrityCheckRequest, IntegrityCheckResponse,
    StepResult, TestCaseResult,
)
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_step import TestStep
from common.db.models.user_story import UserStory


class IntegrityCheckService:
    """
    Orchestrator for integrity check runs.

    Delegates to:
    - LoginService            — handles login automation
    - IntegrityCheckRepository — handles DB persistence
    - BrowserRunner           — drives the actual browser
    - LLM                     — diagnoses failures
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._repo = IntegrityCheckRepository(db)
        self._auth_svc = AuthSessionService(db)
        self._login_svc = LoginService()
        self._screenshots_base = Path(settings.SCREENSHOTS_DIR)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_check(
        self,
        request: IntegrityCheckRequest,
        triggered_by: Optional[int] = None,
    ) -> IntegrityCheckResponse:
        """Execute a full integrity check and return the result."""
        start_time = datetime.utcnow()
        login_llm_diagnosis: Optional[str] = None
        login_error: Optional[str] = None

        resolved_engine = resolve_runner_engine(request.browser_engine)
        require_steel_key_if_steel_engine(resolved_engine)

        saved_sess = await self._auth_svc.get_active_session(request.project_id)
        cred_saved = bool(saved_sess and saved_sess.auth_type == "credentials")
        req_cred = bool(
            request.credentials
            and request.credentials.username
            and request.credentials.password
        )
        has_creds = cred_saved or req_cred
        if request.login_mode == "google_sso" and has_creds:
            auth_method = "google_sso"
        elif has_creds:
            auth_method = "credentials"
        else:
            auth_method = "none"

        relax_captcha = bool(
            steel_cdp_enabled_for_engine(resolved_engine) and settings.STEEL_SOLVE_CAPTCHA
        )

        run = await self._repo.create_run(
            project_id=request.project_id,
            app_url=request.app_url,
            browser_engine=effective_browser_label(request.browser_engine),
            auth_method=auth_method,
            triggered_by=triggered_by,
        )
        await self.db.commit()

        screenshots_dir = self._screenshots_base / str(request.project_id) / str(run.id)
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        all_screenshots: List[str] = []
        test_case_results: List[TestCaseResult] = []
        app_reachable = False
        login_successful: Optional[bool] = None

        async with get_browser_runner(
            headless=False,
            engine=request.browser_engine,
            steel_target_url=request.app_url,
        ) as runner:
            try:
                await runner.start_network_logging()

                nav_result = await runner.navigate(request.app_url)
                app_reachable = nav_result.success

                await runner.wait(3000)

                ss = await self._capture_screenshot(
                    runner, request.project_id, run.id,
                    0, "navigate", screenshots_dir,
                )
                if ss:
                    all_screenshots.append(ss)

                if not app_reachable:
                    return await self._abort_run(
                        run, start_time, app_reachable=False,
                        error=f"Application not reachable: {nav_result.error}",
                        extra_screenshots=all_screenshots,
                    )

                html_after_nav = await runner.get_page_html()
                cur_url = await runner.get_current_url()
                cap_sig = detect_captcha_signals(html_after_nav, cur_url or "")
                if cap_sig and not relax_captcha:
                    err = (
                        "CAPTCHA detected before login. Integrity checks require a staging/test "
                        f"build without CAPTCHA or with test keys. ({cap_sig})"
                    )
                    return await self._abort_run(
                        run, start_time, app_reachable=True, error=err,
                        extra_screenshots=all_screenshots,
                    )
                if cap_sig and relax_captcha:
                    logger.warning(
                        "[IC] CAPTCHA-like signals on landing (%s) — continuing (Steel CAPTCHA solve may apply)",
                        cap_sig,
                    )

                login_result, login_llm_diagnosis = await self._attempt_login(
                    runner,
                    request,
                    screenshots_dir,
                    run.id,
                    all_screenshots,
                    relax_captcha=relax_captcha,
                )
                login_successful = login_result.success
                if not login_result.success and login_result.method != "skipped":
                    login_error = login_result.error

                ss = await self._capture_screenshot(
                    runner, request.project_id, run.id,
                    0, "post_login", screenshots_dir,
                )
                if ss:
                    all_screenshots.append(ss)

                if not login_result.success and login_result.method != "skipped":
                    logger.warning(f"[IC] Login failed: {login_result.error}")

                test_cases = await self._get_integrity_test_cases(request.project_id)
                logger.info(f"[IC] {len(test_cases)} test case(s) flagged for integrity check")

                if not test_cases:
                    return await self._finalise_run(
                        run, test_case_results, start_time, app_reachable,
                        login_successful, extra_screenshots=all_screenshots,
                        error="No test cases flagged for integrity check",
                        login_error=login_error,
                        login_llm_diagnosis=login_llm_diagnosis,
                    )

                for tc in test_cases:
                    tc_result = await self._execute_test_case(
                        tc, runner, run.id, request.project_id, screenshots_dir,
                    )
                    test_case_results.append(tc_result)

            except Exception as e:
                logger.error(f"[IC] Unexpected error: {e}")
                return await self._abort_run(
                    run, start_time, app_reachable, error=str(e),
                    extra_screenshots=all_screenshots,
                    login_error=login_error,
                    login_llm_diagnosis=login_llm_diagnosis,
                )
            finally:
                logger.info("[IC] Holding browser open for observation (5s)…")
                await runner.wait(5000)

        return await self._finalise_run(
            run, test_case_results, start_time, app_reachable, login_successful,
            extra_screenshots=all_screenshots,
            login_error=login_error,
            login_llm_diagnosis=login_llm_diagnosis,
        )

    async def get_history(self, project_id: int, limit: int = 20) -> List[dict]:
        """Return recent integrity check runs as serialisable dicts."""
        runs = await self._repo.get_run_history(project_id, limit)
        return [self._serialise_run(r) for r in runs]

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def _attempt_login(
        self,
        runner: BrowserRunner,
        request: IntegrityCheckRequest,
        screenshots_dir: Path,
        run_id: int,
        all_screenshots: List[str],
        *,
        relax_captcha: bool = False,
    ) -> Tuple[LoginResult, Optional[str]]:
        username = password = None
        login_url: Optional[str] = None
        custom_selectors = None

        if request.credentials:
            username = request.credentials.username
            password = request.credentials.password
            login_url = request.credentials.login_url
            if request.credentials.username_selector or request.credentials.password_selector:
                custom_selectors = {
                    "username_selector": request.credentials.username_selector,
                    "password_selector": request.credentials.password_selector,
                    "submit_selector": request.credentials.submit_selector,
                }

        saved = await self._auth_svc.get_active_session(request.project_id)
        if saved and saved.auth_type == "credentials":
            decrypted = self._auth_svc.decrypt_credentials(saved)
            if decrypted:
                username = username or decrypted.get("username")
                password = password or decrypted.get("password")

        has_creds = bool(username and password)

        if not has_creds:
            logger.info("[IC] Login: no username/password — skipping auth.")
            return LoginResult(success=True, method="skipped"), None

        async def snap_fail(label: str) -> None:
            path = await self._capture_screenshot(
                runner, request.project_id, run_id, 0, label, screenshots_dir,
            )
            if path:
                all_screenshots.append(path)

        if request.login_mode == "google_sso":
            logger.info("[IC] Login: login_mode=google_sso (in-page Google + account credentials)")
            last = await self._login_svc.google_sso_login_with_credentials(
                runner,
                request.app_url,
                username,
                password,
                login_url=login_url,
                relax_captcha=relax_captcha,
            )
            if not last.success:
                await snap_fail("login_google_sso_failed")
        else:
            logger.info("[IC] Login: login_mode=app_form (username/password on app)")
            last = await self._login_svc.login(
                runner,
                request.app_url,
                username=username,
                password=password,
                custom_selectors=custom_selectors,
                login_url=login_url,
                storage_state=None,
                relax_captcha=relax_captcha,
            )
            if not last.success:
                await snap_fail("login_credentials_failed")

        diag: Optional[str] = None
        if not last.success:
            diag = await self._diagnose_login_failure(runner, last.error or "Login failed")
        return last, diag

    # ------------------------------------------------------------------
    # Test case execution
    # ------------------------------------------------------------------

    async def _execute_test_case(
        self,
        tc: TestCase,
        runner: BrowserRunner,
        run_id: int,
        project_id: int,
        screenshots_dir: Path,
    ) -> TestCaseResult:
        tc_start = datetime.utcnow()
        step_results: List[StepResult] = []
        steps_passed = steps_failed = 0

        for step in sorted(tc.steps, key=lambda s: s.step_number):
            sr = await self._execute_step(step, tc, runner, run_id, project_id, screenshots_dir)
            step_results.append(sr)
            if sr.status == "passed":
                steps_passed += 1
            else:
                steps_failed += 1
                break

        tc_duration = int((datetime.utcnow() - tc_start).total_seconds() * 1000)
        tc_status = "passed" if steps_failed == 0 else "failed"
        return TestCaseResult(
            test_case_id=tc.id, title=tc.title, status=tc_status,
            steps_total=len(tc.steps), steps_passed=steps_passed,
            steps_failed=steps_failed, step_results=step_results,
            duration_ms=tc_duration,
        )

    async def _execute_step(
        self,
        step: TestStep,
        tc: TestCase,
        runner: BrowserRunner,
        run_id: int,
        project_id: int,
        screenshots_dir: Path,
    ) -> StepResult:
        step_start = datetime.utcnow()
        action = step.action.value if hasattr(step.action, "value") else str(step.action)
        screenshot_url: Optional[str] = None
        llm_diagnosis: Optional[str] = None

        result = await dispatch_action(runner, action, step.target, step.value)

        screenshot_url = await self._capture_screenshot(
            runner, project_id, run_id, step.step_number, action, screenshots_dir,
        )

        if not result.success:
            llm_diagnosis = await self._diagnose_failure(
                runner, tc.title, step.step_number, action,
                step.target, step.value, result.error or "",
            )

        duration_ms = int((datetime.utcnow() - step_start).total_seconds() * 1000)

        await self._repo.save_step_result(
            run_id=run_id, test_case_id=tc.id,
            test_case_title=tc.title, test_case_status=None,
            test_case_duration_ms=None, step_number=step.step_number,
            action=action, description=step.description,
            status="passed" if result.success else "failed",
            error=result.error, screenshot_path=screenshot_url,
            llm_diagnosis=llm_diagnosis, duration_ms=duration_ms,
        )
        await self.db.commit()

        return StepResult(
            step_number=step.step_number, action=action,
            description=step.description,
            status="passed" if result.success else "failed",
            duration_ms=duration_ms, error=result.error,
            screenshot_path=screenshot_url, llm_diagnosis=llm_diagnosis,
        )

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    async def _capture_screenshot(
        self, runner: BrowserRunner, project_id: int, run_id: int,
        step_number: int, action: str, screenshots_dir: Path,
    ) -> Optional[str]:
        try:
            safe_action = "".join(c if c.isalnum() else "_" for c in action)
            filename = f"step_{step_number:03d}_{safe_action}.png"
            filepath = screenshots_dir / filename
            await runner.screenshot(path=str(filepath))
            return f"/screenshots/{project_id}/{run_id}/{filename}"
        except Exception as e:
            logger.warning(f"[IC] Screenshot capture failed: {e}")
            return None

    # ------------------------------------------------------------------
    # LLM failure diagnosis
    # ------------------------------------------------------------------

    async def _invoke_diagnosis_llm(
        self, system_prompt: str, user_prompt: str, runner: BrowserRunner,
    ) -> Optional[str]:
        snap = await runner.screenshot()
        b64 = snap.screenshot_b64 if snap.success else None

        if b64:
            try:
                llm = get_llm_client(provider="gemini")
                if isinstance(llm, LiteLLMClient):
                    response = await llm.chat_with_text_and_image_b64(
                        system_prompt, user_prompt, b64,
                        temperature=0.3, max_tokens=400,
                    )
                    return response.content.strip()
            except Exception as e:
                logger.warning(f"[IC] LLM vision diagnosis failed (gemini): {e}")

        for provider in (None, "gemini"):
            try:
                llm = get_llm_client(provider=provider)
                response = await llm.chat(
                    messages=[
                        Message(role="system", content=system_prompt),
                        Message(role="user", content=user_prompt),
                    ],
                    temperature=0.3, max_tokens=400,
                )
                return response.content.strip()
            except Exception as e:
                label = provider or "default"
                logger.warning(f"[IC] LLM diagnosis failed ({label}): {e}")
                continue
        return None

    async def _diagnose_failure(
        self, runner: BrowserRunner, tc_title: str, step_number: int,
        action: str, target: Optional[str], value: Optional[str], error: str,
    ) -> Optional[str]:
        current_url = await runner.get_current_url()
        html = await runner.get_page_html()
        net = await runner.get_network_log_summary(80)
        system_p, user_p = build_failure_diagnosis_prompt(
            test_case_title=tc_title, step_number=step_number,
            action=action, target=target or "", value=value or "",
            error=error, current_url=current_url, page_title="",
            html_snippet=html,
            network_log_summary=net,
        )
        return await self._invoke_diagnosis_llm(system_p, user_p, runner)

    async def _diagnose_login_failure(
        self, runner: BrowserRunner, error: str,
    ) -> Optional[str]:
        current_url = await runner.get_current_url()
        html = await runner.get_page_html()
        net = await runner.get_network_log_summary(80)
        system_p, user_p = build_login_failure_diagnosis_prompt(
            error=error, current_url=current_url,
            html_snippet=html, network_log_summary=net,
        )
        return await self._invoke_diagnosis_llm(system_p, user_p, runner)

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _abort_run(
        self, run: IntegrityCheckRun, start_time: datetime,
        app_reachable: bool, error: str,
        extra_screenshots: Optional[List[str]] = None,
        login_error: Optional[str] = None,
        login_llm_diagnosis: Optional[str] = None,
    ) -> IntegrityCheckResponse:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        await self._repo.finalise_run(
            run, "error", app_reachable, None, 0, 0, 0, duration_ms, error,
        )
        await self.db.commit()
        return IntegrityCheckResponse(
            project_id=run.project_id, status="error",
            app_reachable=app_reachable, test_cases_total=0,
            test_cases_passed=0, test_cases_failed=0,
            test_case_results=[], duration_ms=duration_ms,
            checked_at=datetime.utcnow(), error=error,
            screenshots=list(extra_screenshots or []),
            login_error=login_error,
            login_llm_diagnosis=login_llm_diagnosis,
        )

    async def _finalise_run(
        self, run: IntegrityCheckRun, results: List[TestCaseResult],
        start_time: datetime, app_reachable: bool,
        login_successful: Optional[bool],
        extra_screenshots: Optional[List[str]] = None,
        error: Optional[str] = None,
        login_error: Optional[str] = None,
        login_llm_diagnosis: Optional[str] = None,
    ) -> IntegrityCheckResponse:
        passed = sum(1 for r in results if r.status == "passed")
        failed = len(results) - passed
        overall = "passed" if failed == 0 else "failed"
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        await self._repo.finalise_run(
            run, overall, app_reachable, login_successful,
            len(results), passed, failed, duration_ms, error,
        )
        await self.db.commit()

        all_screenshots = list(extra_screenshots or [])
        all_screenshots.extend(
            sr.screenshot_path for tc in results
            for sr in tc.step_results if sr.screenshot_path
        )
        return IntegrityCheckResponse(
            project_id=run.project_id, status=overall,
            app_reachable=app_reachable, login_successful=login_successful,
            test_cases_total=len(results), test_cases_passed=passed,
            test_cases_failed=failed, test_case_results=results,
            screenshots=all_screenshots, duration_ms=duration_ms,
            checked_at=datetime.utcnow(), error=error,
            login_error=login_error,
            login_llm_diagnosis=login_llm_diagnosis,
        )

    # ------------------------------------------------------------------
    # Data retrieval
    # ------------------------------------------------------------------

    async def _get_integrity_test_cases(self, project_id: int) -> List[TestCase]:
        us_result = await self.db.execute(
            select(UserStory.id)
            .where(UserStory.project_id == project_id)
            .where(UserStory.integrity_check == True)
        )
        integrity_us_ids = [r[0] for r in us_result.fetchall()]

        conditions = [TestCase.integrity_check == True]
        if integrity_us_ids:
            conditions.append(TestCase.user_story_id.in_(integrity_us_ids))

        result = await self.db.execute(
            select(TestCase)
            .options(selectinload(TestCase.steps))
            .where(TestCase.project_id == project_id)
            .where(or_(*conditions))
            .order_by(TestCase.id)
        )
        return list(result.scalars().all())

    @staticmethod
    def _serialise_run(run: IntegrityCheckRun) -> dict:
        return {
            "id": run.id,
            "project_id": run.project_id,
            "status": run.status,
            "app_url": run.app_url,
            "app_reachable": run.app_reachable,
            "login_successful": run.login_successful,
            "browser_engine": run.browser_engine,
            "auth_method": run.auth_method,
            "test_cases_total": run.test_cases_total,
            "test_cases_passed": run.test_cases_passed,
            "test_cases_failed": run.test_cases_failed,
            "duration_ms": run.duration_ms,
            "error": run.error,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
