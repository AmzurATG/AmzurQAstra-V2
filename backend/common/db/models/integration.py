"""
Project Integration Model

Stores integration configurations for each project (Jira, Redmine, Azure DevOps, Slack, etc.)
Uses JSONB for flexible config storage with type-specific validation in Python.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from common.db.base import BaseModel


class IntegrationType(str, enum.Enum):
    """Supported integration types"""
    jira = "jira"
    redmine = "redmine"
    azure_devops = "azure_devops"
    slack = "slack"
    confluence = "confluence"
    github = "github"
    gitlab = "gitlab"
    teams = "teams"


class IntegrationCategory(str, enum.Enum):
    """Integration category groupings"""
    project_management = "project_management"
    communication = "communication"
    documentation = "documentation"
    version_control = "version_control"


class SyncStatus(str, enum.Enum):
    """Sync status for integrations"""
    idle = "idle"
    syncing = "syncing"
    success = "success"
    failed = "failed"


class ProjectIntegration(BaseModel):
    """
    Project Integration model.
    
    Stores configuration for external tool integrations on a per-project basis.
    The config field uses JSONB to store type-specific configuration flexibly.
    Sensitive data (tokens, passwords) should be encrypted before storage.
    """
    
    __tablename__ = "project_integrations"
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project = relationship("Project", backref="integrations")
    
    # Integration type and category
    integration_type = Column(
        Enum(IntegrationType),
        nullable=False,
        index=True
    )
    integration_category = Column(
        Enum(IntegrationCategory),
        nullable=False
    )
    
    # Display name (e.g., "Production Jira", "QA Slack Channel")
    name = Column(String(255), nullable=True)
    
    # Configuration stored as JSONB (type-specific, validated in Python)
    # Example for Jira: {"base_url": "...", "email": "...", "api_token": "encrypted...", "project_key": "..."}
    config = Column(JSONB, nullable=False, default={})
    
    # Status flags
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # Sync tracking
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(
        Enum(SyncStatus),
        default=SyncStatus.idle,
        nullable=False
    )
    last_sync_error = Column(Text, nullable=True)
    items_synced = Column(Integer, default=0)
    
    # Who configured this integration
    configured_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    configured_by = relationship("User")
    
    def __repr__(self):
        return f"<ProjectIntegration(id={self.id}, project_id={self.project_id}, type={self.integration_type})>"
    
    @property
    def display_name(self) -> str:
        """Return display name or default based on type"""
        if self.name:
            return self.name
        return self.integration_type.value.replace("_", " ").title()
