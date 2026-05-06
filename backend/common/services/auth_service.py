"""
Authentication Service
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from common.db.models.user import User
from common.schemas.user import UserCreate, UserUpdate, Token
from common.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from config import settings


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        hashed_pwd = hash_password(user_data.password)
        user = User(
            email=user_data.email,
            hashed_password=hashed_pwd,
            full_name=user_data.full_name,
            role=user_data.role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
    
    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    async def login(self, email: str, password: str, remember_me: bool = False) -> Optional[Token]:
        """Login and return JWT tokens."""
        user = await self.authenticate(email, password)
        if not user:
            return None
        
        access_token = create_access_token(subject=str(user.id))
        
        if remember_me:
            refresh_expires = timedelta(days=settings.REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS)
            refresh_token = create_refresh_token(subject=str(user.id), expires_delta=refresh_expires)
        else:
            refresh_token = create_refresh_token(subject=str(user.id))
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_tokens(self, refresh_token_str: str) -> Optional[Token]:
        """Validate refresh JWT and return a new access + refresh pair."""
        try:
            payload = verify_token(refresh_token_str)
        except JWTError:
            return None
        if payload.get("type") != "refresh":
            return None
        # Reject refresh tokens issued by a previous server process
        from common.utils.security import BOOT_NONCE
        if payload.get("nonce") != BOOT_NONCE:
            return None
        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            return None
        user = await self.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None
        return Token(
            access_token=create_access_token(subject=str(user.id)),
            refresh_token=create_refresh_token(subject=str(user.id)),
            token_type="bearer",
        )
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.flush()
        await self.db.refresh(user)
        return user
