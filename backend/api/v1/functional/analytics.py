"""Project Test Report Analytics (functional v1)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.api.deps import get_current_active_user
from common.db.database import get_db
from common.db.models.user import User
from features.functional.schemas.analytics import ProjectAnalyticsResponse
from features.functional.services.analytics import WINDOW_DAYS, build_functional_project_analytics
from features.functional.services.analytics.sources import AnalyticsSource, parse_source

router = APIRouter()


@router.get("/project", response_model=ProjectAnalyticsResponse)
async def project_analytics(
    project_id: int = Query(...),
    source: str = Query("functional"),
    window: str = Query("30d"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if window not in WINDOW_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="window must be one of: 7d, 30d, 90d",
        )
    try:
        src = parse_source(source)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if src != AnalyticsSource.FUNCTIONAL:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Analytics source '{src.value}' is not available yet.",
        )
    return await build_functional_project_analytics(
        db, current_user, project_id, window
    )
