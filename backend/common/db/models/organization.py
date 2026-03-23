"""
Organization Model (Multi-tenancy support)
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship

from common.db.base import BaseModel


class Organization(BaseModel):
    """Organization model for multi-tenancy."""
    
    __tablename__ = "organizations"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"
