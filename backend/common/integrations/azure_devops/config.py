"""
Azure DevOps Configuration Schema
"""

from typing import Optional, List
from pydantic import Field
from ..base import BaseIntegrationConfig


class AzureDevOpsConfig(BaseIntegrationConfig):
    """Configuration schema for Azure DevOps integration"""
    
    organization_url: str = Field(
        ...,
        description="Azure DevOps organization URL (e.g., https://dev.azure.com/myorg)",
        examples=["https://dev.azure.com/myorg"]
    )
    
    personal_access_token: str = Field(
        ...,
        description="Personal Access Token (PAT) with Work Items read/write scope"
    )
    
    project_name: Optional[str] = Field(
        None,
        description="Azure DevOps project name"
    )
    
    area_path: Optional[str] = Field(
        None,
        description="Area path to filter work items"
    )
    
    work_item_types: List[str] = Field(
        default=["User Story", "Bug"],
        description="Work item types to import"
    )
    
    sync_test_results: bool = Field(
        default=True,
        description="Whether to sync test results back to work items"
    )
