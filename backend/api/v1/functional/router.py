"""
Functional Testing Feature Router
"""
from fastapi import APIRouter

from api.v1.functional.requirements import router as requirements_router
from api.v1.functional.test_cases import router as test_cases_router
from api.v1.functional.test_steps import router as test_steps_router
from api.v1.functional.test_runs import router as test_runs_router
from api.v1.functional.integrity_check import router as integrity_check_router
from api.v1.functional.integrations import router as integrations_router
from api.v1.functional.user_stories import router as user_stories_router
from api.v1.functional.dashboard import router as dashboard_router


router = APIRouter()

router.include_router(
    requirements_router,
    prefix="/requirements",
    tags=["Functional - Requirements"],
)
router.include_router(
    test_cases_router,
    prefix="/test-cases",
    tags=["Functional - Test Cases"],
)
router.include_router(
    test_steps_router,
    prefix="/test-steps",
    tags=["Functional - Test Steps"],
)
router.include_router(
    test_runs_router,
    prefix="/test-runs",
    tags=["Functional - Test Runs"],
)
router.include_router(
    integrity_check_router,
    prefix="/integrity-check",
    tags=["Functional - Integrity Check"],
)
router.include_router(
    integrations_router,
    prefix="/integrations",
    tags=["Functional - Integrations"],
)
router.include_router(
    user_stories_router,
    prefix="/user-stories",
    tags=["Functional - User Stories"],
)
router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Functional - Dashboard"],
)
