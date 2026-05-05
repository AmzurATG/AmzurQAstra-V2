"""
API v1 Main Router
Combines all feature routers
"""
from fastapi import APIRouter

from api.v1.common.auth import router as auth_router
from api.v1.common.signup import router as signup_router
from api.v1.common.password_reset import router as password_reset_router
from api.v1.common.users import router as users_router
from api.v1.common.projects import router as projects_router
from api.v1.common.integrations import router as integrations_router
from api.v1.functional.router import router as functional_router


api_router = APIRouter()

# Common routes
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(signup_router, prefix="/auth", tags=["Signup"])
api_router.include_router(password_reset_router, prefix="/auth", tags=["Password Reset"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(projects_router, prefix="/projects", tags=["Projects"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])

# Feature routes
api_router.include_router(functional_router, prefix="/functional", tags=["Functional Testing"])

# Future feature routes
# api_router.include_router(api_testing_router, prefix="/api-testing", tags=["API Testing"])
# api_router.include_router(performance_router, prefix="/performance", tags=["Performance Testing"])
