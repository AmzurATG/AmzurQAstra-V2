"""Dashboard aggregate metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from features.functional.schemas.dashboard import DashboardOverviewResponse
from features.functional.services.dashboard_service import fetch_dashboard_overview

router = APIRouter()


@router.get("/overview", response_model=DashboardOverviewResponse)
async def dashboard_overview(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregates projects, test cases, runs, and recent activity for the current user."""
    data = await fetch_dashboard_overview(db, current_user)
    return DashboardOverviewResponse(**data)
