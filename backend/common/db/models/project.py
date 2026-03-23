"""
Project Model
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from common.db.base import BaseModel


class Project(BaseModel):
    """Project model - container for test cases and requirements."""
    
    __tablename__ = "projects"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Application under test
    app_url = Column(String(500), nullable=True)
    app_credentials = Column(JSONB, nullable=True)  # Encrypted credentials
    
    # Project status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="owned_projects")
    
    # Organization
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    organization = relationship("Organization", back_populates="projects")
    
    # Integration settings
    jira_project_key = Column(String(50), nullable=True)
    azure_devops_project = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"
