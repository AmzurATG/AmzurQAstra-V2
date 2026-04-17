"""
Base Integration Interfaces

Abstract base classes that define the contract for all integrations.
Uses Strategy Pattern - each integration implements these interfaces.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Type, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class BaseIntegrationConfig(BaseModel):
    """Base configuration schema that all integrations extend"""

    sync_scope: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Persisted sync preferences (non-sensitive): issue types, sprint scope, etc."
        ),
    )

    class Config:
        extra = "forbid"  # Reject unknown fields


class UserStoryData(BaseModel):
    """Standardized user story format from any PM tool"""
    external_id: str
    external_key: str
    title: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    item_type: Optional[str] = "story"  # epic, story, bug, task, etc.
    parent_key: Optional[str] = None  # Key of parent item (epic, feature, etc.)
    story_points: Optional[int] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    labels: List[str] = []
    sprint_id: Optional[str] = None  # External sprint ID
    sprint_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    external_url: Optional[str] = None


class ProjectData(BaseModel):
    """Standardized project format from any PM tool"""
    key: str
    name: str
    description: Optional[str] = None


class TestResultData(BaseModel):
    """Test result to sync back to PM tool"""
    status: str  # passed, failed, skipped
    test_case_name: str
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    screenshot_url: Optional[str] = None
    executed_at: datetime


class BaseIntegration(ABC):
    """
    Abstract base class for all integrations.
    
    Every integration must implement:
    - get_config_schema(): Return the Pydantic config class
    - test_connection(): Verify credentials are valid
    - get_projects(): List available projects/workspaces
    """
    
    integration_type: str = ""
    category: str = ""
    display_name: str = ""
    icon: str = ""  # Emoji or icon name
    
    def __init__(self, config: dict):
        """
        Initialize integration with config dict.
        Config is validated against the schema.
        """
        schema = self.get_config_schema()
        self.config = schema(**config)
        self._client = None
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> Type[BaseIntegrationConfig]:
        """Return the Pydantic schema class for this integration's config"""
        pass
    
    @classmethod
    def get_config_fields(cls) -> List[dict]:
        """Return config field definitions for frontend forms"""
        schema = cls.get_config_schema()
        fields = []
        for name, field in schema.model_fields.items():
            field_info = {
                "name": name,
                "label": name.replace("_", " ").title(),
                "type": "password" if "token" in name or "password" in name or "secret" in name or "key" in name.lower() else "text",
                "required": field.is_required(),
                "description": field.description or "",
            }
            fields.append(field_info)
        return fields
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if the integration credentials are valid.
        
        Returns:
            True if connection successful
            
        Raises:
            IntegrationConnectionError: If connection fails
            IntegrationAuthError: If authentication fails
        """
        pass
    
    @abstractmethod
    async def get_projects(self) -> List[ProjectData]:
        """
        List available projects/workspaces from the external tool.
        
        Returns:
            List of ProjectData objects
        """
        pass


class ProjectManagementIntegration(BaseIntegration):
    """
    Extended interface for Project Management tools.
    (Jira, Redmine, Azure DevOps, GitHub Issues)
    
    Adds methods for:
    - Fetching user stories/issues
    - Syncing test results back
    """
    
    category = "project_management"
    
    @abstractmethod
    async def fetch_user_stories(
        self, 
        project_key: str,
        issue_types: Optional[List[str]] = None,
        updated_since: Optional[datetime] = None
    ) -> List[UserStoryData]:
        """
        Fetch user stories/issues from the PM tool.
        
        Args:
            project_key: The project identifier
            issue_types: Filter by issue types (e.g., ['Story', 'Bug'])
            updated_since: Only fetch items updated after this time
            
        Returns:
            List of UserStoryData objects
        """
        pass
    
    @abstractmethod
    async def sync_test_result(
        self, 
        issue_key: str, 
        result: TestResultData
    ) -> bool:
        """
        Post test results back to the PM tool (as comment/update).
        
        Args:
            issue_key: The issue identifier
            result: Test result data
            
        Returns:
            True if sync successful
        """
        pass
    
    async def get_issue(self, issue_key: str) -> Optional[UserStoryData]:
        """
        Get a single issue by key.
        Default implementation - can be overridden for efficiency.
        """
        pass


class CommunicationIntegration(BaseIntegration):
    """
    Extended interface for Communication tools.
    (Slack, Microsoft Teams)
    """
    
    category = "communication"
    
    @abstractmethod
    async def send_notification(
        self, 
        message: str,
        channel: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Send a notification message.
        
        Args:
            message: The message text
            channel: Target channel (uses default if not specified)
            attachments: Rich message attachments
            
        Returns:
            True if sent successfully
        """
        pass
    
    async def send_test_report(
        self,
        run_name: str,
        total: int,
        passed: int,
        failed: int,
        skipped: int,
        duration_seconds: int,
        report_url: Optional[str] = None
    ) -> bool:
        """
        Send a formatted test run report.
        Default implementation uses send_notification.
        """
        status_emoji = "✅" if failed == 0 else "❌"
        message = f"""
{status_emoji} *Test Run Complete: {run_name}*
• Total: {total}
• Passed: {passed}
• Failed: {failed}
• Skipped: {skipped}
• Duration: {duration_seconds}s
"""
        if report_url:
            message += f"\n<{report_url}|View Full Report>"
        
        return await self.send_notification(message)


class DocumentationIntegration(BaseIntegration):
    """
    Extended interface for Documentation tools.
    (Confluence, Notion)
    """
    
    category = "documentation"
    
    @abstractmethod
    async def get_spaces(self) -> List[dict]:
        """List available spaces/workspaces"""
        pass
    
    @abstractmethod
    async def get_pages(self, space_key: str) -> List[dict]:
        """List pages in a space"""
        pass
    
    @abstractmethod
    async def get_page_content(self, page_id: str) -> str:
        """Get page content as text"""
        pass
    
    async def extract_requirements(self, page_id: str) -> List[dict]:
        """
        Extract requirements from a documentation page.
        Default implementation returns raw content.
        """
        content = await self.get_page_content(page_id)
        return [{"content": content}]
