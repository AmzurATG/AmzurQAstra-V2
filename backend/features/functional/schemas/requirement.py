"""
Requirement Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, computed_field

from features.functional.db.models.requirement import RequirementSourceType


class RequirementBase(BaseModel):
    """Base requirement schema."""
    title: str
    content: Optional[str] = None
    source_type: RequirementSourceType = RequirementSourceType.MANUAL


class RequirementCreate(RequirementBase):
    """Schema for creating a requirement."""
    project_id: int
    source_url: Optional[str] = None
    source_id: Optional[str] = None


class RequirementUpdate(BaseModel):
    """Schema for updating a requirement."""
    title: Optional[str] = None
    content: Optional[str] = None


class RequirementResponse(RequirementBase):
    """Schema for requirement response."""
    id: int
    project_id: int
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Additional fields for frontend
    test_cases_count: int = 0
    status: str = "processed"
    
    @computed_field
    @property
    def source(self) -> str:
        """Alias for source_type for frontend compatibility."""
        return self.source_type.value if self.source_type else "manual"
    
    class Config:
        from_attributes = True
