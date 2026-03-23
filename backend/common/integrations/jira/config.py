"""
Jira Configuration Schema
"""

from typing import Optional, List
from pydantic import Field
from ..base import BaseIntegrationConfig


class JiraConfig(BaseIntegrationConfig):
    """Configuration schema for Jira integration"""
    
    base_url: str = Field(
        ...,
        description="Jira Cloud or Server URL (e.g., https://company.atlassian.net)",
        examples=["https://company.atlassian.net"]
    )
    
    email: str = Field(
        ...,
        description="Email address associated with your Jira account"
    )
    
    api_token: str = Field(
        ...,
        description="Jira API token (from https://id.atlassian.com/manage-profile/security/api-tokens)"
    )
    
    project_key: Optional[str] = Field(
        None,
        description="Default Jira project key to sync (e.g., PROJ)"
    )
    
    project_name: Optional[str] = Field(
        None,
        description="Display name of the Jira project (for UI display)"
    )
    
    issue_types: List[str] = Field(
        default=["Story", "Bug", "Task"],
        description="Issue types to import as user stories"
    )
    
    jql_filter: Optional[str] = Field(
        None,
        description="Custom JQL filter for fetching issues"
    )
    
    sync_comments: bool = Field(
        default=True,
        description="Whether to sync test results as Jira comments"
    )
    
    sync_labels: bool = Field(
        default=True,
        description="Whether to sync labels/tags"
    )
