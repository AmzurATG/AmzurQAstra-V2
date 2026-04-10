"""
Requirement Model
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from common.db.base import BaseModel


class RequirementSourceType(str, enum.Enum):
    """Requirement source types."""
    UPLOAD = "upload"
    JIRA = "jira"
    AZURE_DEVOPS = "azure_devops"
    CONFLUENCE = "confluence"
    MANUAL = "manual"


class Requirement(BaseModel):
    """Requirement document model."""
    
    __tablename__ = "requirements"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)  # Parsed content
    
    # Source information (persist enum .value to match PostgreSQL requirementsourcetype)
    source_type = Column(
        Enum(
            RequirementSourceType,
            name="requirementsourcetype",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=RequirementSourceType.MANUAL,
    )
    source_url = Column(String(1000), nullable=True)  # Jira link, file path, etc.
    source_id = Column(String(100), nullable=True)  # Jira issue key, etc.
    
    # File storage
    file_path = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(255), nullable=True)  # MIME types can exceed 50 chars (e.g. OOXML)
    
    # Relationships
    test_cases = relationship("TestCase", back_populates="requirement")
    
    def __repr__(self):
        return f"<Requirement(id={self.id}, title='{self.title}')>"
