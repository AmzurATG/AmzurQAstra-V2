"""
User Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr

from common.db.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    email: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.tester


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    is_superuser: bool
    organization_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """Schema for user login."""
    email: str  # Use str instead of EmailStr for login flexibility
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Body for POST /auth/refresh."""
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    exp: datetime
