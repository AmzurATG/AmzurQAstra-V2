"""
Project Schemas
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl


class ProjectBase(BaseModel):
    """Base project schema."""
    name: str
    description: Optional[str] = None
    app_url: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    app_url: Optional[str] = None
    app_credentials: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    jira_project_key: Optional[str] = None
    azure_devops_project: Optional[str] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: int
    is_active: bool
    owner_id: int
    organization_id: Optional[int] = None
    jira_project_key: Optional[str] = None
    azure_devops_project: Optional[str] = None
    has_credentials: bool = False
    app_username: Optional[str] = None
    app_password: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectCredentials(BaseModel):
    """Schema for project credentials."""
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    additional: Optional[Dict[str, Any]] = None
