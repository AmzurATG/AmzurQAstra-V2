"""
UI Discovery API endpoints (under /integrity-check/discover/*).
"""
from typing import List

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.api.deps import get_current_active_user
from common.db.database import get_db
from common.db.models.user import User
from features.functional.schemas.ui_discovery import (
    UiDiscoveryHistoryItem,
    UiDiscoveryLatestResponse,
    UiDiscoveryStartRequest,
    UiDiscoveryStartResponse,
    UiDiscoveryStatusResponse,
)
from features.functional.services.ui_discovery_service import UiDiscoveryService

router = APIRouter()


@router.post("/discover", response_model=UiDiscoveryStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_ui_discovery(
    request: UiDiscoveryStartRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Start async UI discovery — returns run_id immediately."""
    svc = UiDiscoveryService(db)
    return await svc.start_discovery(request)


@router.get("/discover/{run_id}/status", response_model=UiDiscoveryStatusResponse)
async def get_discovery_status(
    run_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll discovery progress or fetch completed inventory."""
    svc = UiDiscoveryService(db)
    return await svc.get_status(run_id)


@router.get("/discover/project/{project_id}/latest", response_model=UiDiscoveryLatestResponse)
async def get_latest_discovery(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Latest completed inventory for generation context."""
    svc = UiDiscoveryService(db)
    return await svc.get_latest(project_id)


@router.get("/discover/history/{project_id}", response_model=List[UiDiscoveryHistoryItem])
async def get_discovery_history(
    project_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Past UI discovery runs for a project."""
    svc = UiDiscoveryService(db)
    items = await svc.get_history(project_id, limit=limit)
    return [UiDiscoveryHistoryItem(**item) for item in items]
