"""
Slack Configuration Schema
"""

from typing import Optional
from pydantic import Field
from ..base import BaseIntegrationConfig


class SlackConfig(BaseIntegrationConfig):
    """Configuration schema for Slack integration"""
    
    webhook_url: str = Field(
        ...,
        description="Slack Incoming Webhook URL"
    )
    
    channel: Optional[str] = Field(
        None,
        description="Default channel to post to (overrides webhook default)"
    )
    
    notify_on_test_complete: bool = Field(
        default=True,
        description="Send notification when test run completes"
    )
    
    notify_on_failure_only: bool = Field(
        default=False,
        description="Only notify when tests fail"
    )
    
    include_screenshot: bool = Field(
        default=True,
        description="Include failure screenshots in notifications"
    )
