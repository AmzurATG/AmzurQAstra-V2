"""
User Model
"""
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from common.db.base import BaseModel


class UserRole(str, enum.Enum):
    """User roles."""
    admin = "admin"
    manager = "manager"
    tester = "tester"
    viewer = "viewer"


class User(BaseModel):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole, name='userrole', create_type=False), default=UserRole.tester, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)  # Default True for existing users
    
    # Signup profile fields
    company_name = Column(String(255), nullable=True)
    country_code = Column(String(10), nullable=True)
    phone_number = Column(String(20), nullable=True)
    
    # Organization
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization", back_populates="users")
    
    # Projects owned
    owned_projects = relationship("Project", back_populates="owner")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
