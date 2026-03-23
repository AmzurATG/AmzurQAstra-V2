"""
Redmine Configuration Schema
"""

from typing import Optional, List
from pydantic import Field
from ..base import BaseIntegrationConfig


class RedmineConfig(BaseIntegrationConfig):
    """Configuration schema for Redmine integration"""
    
    base_url: str = Field(
        ...,
        description="Redmine server URL (e.g., https://redmine.company.com)",
        examples=["https://redmine.company.com"]
    )
    
    api_key: str = Field(
        ...,
        description="Redmine API key (from My Account → API access key)"
    )
    
    project_id: Optional[str] = Field(
        None,
        description="Default Redmine project identifier"
    )
    
    tracker_ids: List[int] = Field(
        default=[],
        description="Tracker IDs to import (e.g., [1, 2] for Bug, Feature)"
    )
    
    sync_notes: bool = Field(
        default=True,
        description="Whether to sync test results as issue notes"
    )
