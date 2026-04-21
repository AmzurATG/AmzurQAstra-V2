"""
Common API Dependencies
"""
from datetime import datetime, timezone
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from common.db.database import get_db
from common.db.models.user import User
from common.utils.security import verify_token, BOOT_NONCE
from config import settings


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # Reject tokens issued by a previous server process
        if payload.get("nonce") != BOOT_NONCE:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    from common.services.auth_service import AuthService
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id))
    
    if user is None:
        raise credentials_exception

    # Reject tokens issued before the user was (re)created (e.g. after DB reset)
    iat = payload.get("iat")
    if iat is not None and user.created_at is not None:
        issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
        created_at = user.created_at.replace(tzinfo=timezone.utc) if user.created_at.tzinfo is None else user.created_at
        if issued_at < created_at:
            raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current user and verify they are a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
