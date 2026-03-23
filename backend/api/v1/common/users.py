"""
User Management Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user, get_current_superuser
from common.schemas.user import UserResponse, UserUpdate


router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user information."""
    from common.services.auth_service import AuthService
    auth_service = AuthService(db)
    
    user = await auth_service.update_user(current_user.id, user_data)
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    from sqlalchemy import select
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users
