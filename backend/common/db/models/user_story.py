"""
User Story Model

Stores user stories imported from external PM tools (Jira, Redmine, Azure DevOps).
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
import enum

from common.db.base import BaseModel


class UserStoryStatus(str, enum.Enum):
    """User story status"""
    open = "open"
    in_progress = "in_progress"
    done = "done"
    blocked = "blocked"
    closed = "closed"


class UserStoryPriority(str, enum.Enum):
    """User story priority"""
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class UserStorySource(str, enum.Enum):
    """Source of the user story"""
    jira = "jira"
    redmine = "redmine"
    azure_devops = "azure_devops"
    manual = "manual"


class UserStoryItemType(str, enum.Enum):
    """Type of item from PM tool"""
    epic = "epic"
    story = "story"
    bug = "bug"
    task = "task"
    subtask = "subtask"
    feature = "feature"
    requirement = "requirement"
    other = "other"


class UserStory(BaseModel):
    """
    User Story model.
    
    Represents a user story imported from external tools or created manually.
    Links to requirements and test cases for traceability.
    """
    
    __tablename__ = "user_stories"
    
    # Foreign key to project
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    project = relationship("Project", backref="user_stories")
    
    # External system references
    external_id = Column(String(100), nullable=True)  # ID in external system
    external_key = Column(String(50), nullable=True, index=True)  # e.g., "PROJ-123"
    external_url = Column(String(500), nullable=True)  # Link to external system
    
    # Source tracking
    source = Column(
        Enum(UserStorySource),
        default=UserStorySource.manual,
        nullable=False
    )
    integration_id = Column(Integer, ForeignKey("project_integrations.id", ondelete="SET NULL"), nullable=True)
    integration = relationship("ProjectIntegration")
    
    # Story content
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    acceptance_criteria = Column(Text, nullable=True)
    
    # Status and priority
    status = Column(
        Enum(UserStoryStatus),
        default=UserStoryStatus.open,
        nullable=False
    )
    priority = Column(
        Enum(UserStoryPriority),
        default=UserStoryPriority.medium,
        nullable=False
    )
    
    # Item type and hierarchy
    item_type = Column(
        Enum(UserStoryItemType),
        default=UserStoryItemType.story,
        nullable=False
    )
    parent_key = Column(String(100), nullable=True)  # External key of parent (epic, feature, etc.)
    
    # Metadata
    story_points = Column(Integer, nullable=True)
    assignee = Column(String(255), nullable=True)
    reporter = Column(String(255), nullable=True)
    labels = Column(ARRAY(String), default=[], nullable=False)
    
    # Sprint information
    sprint_id = Column(String(50), nullable=True, index=True)  # External sprint ID
    sprint_name = Column(String(255), nullable=True)
    
    # Integrity check flag - when true, test cases under this story run in integrity checks
    integrity_check = Column(Boolean, default=False, nullable=False)
    
    # Sync tracking
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    external_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # External dates (from source system)
    external_created_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<UserStory(id={self.id}, key='{self.external_key}', title='{self.title[:30]}...')>"
    
    @property
    def display_key(self) -> str:
        """Return external key or internal ID"""
        return self.external_key or f"US-{self.id}"
