"""
Slack Integration Client

Implements CommunicationIntegration interface for Slack.
"""

from typing import List, Optional, Type
import httpx

from ..base import (
    CommunicationIntegration,
    BaseIntegrationConfig,
    ProjectData,
)
from ..exceptions import (
    IntegrationConnectionError,
    IntegrationAuthError,
)
from .config import SlackConfig


class SlackIntegration(CommunicationIntegration):
    """
    Slack integration using Incoming Webhooks.
    """
    
    integration_type = "slack"
    category = "communication"
    display_name = "Slack"
    icon = "💬"
    
    config: SlackConfig
    
    @classmethod
    def get_config_schema(cls) -> Type[BaseIntegrationConfig]:
        return SlackConfig
    
    async def test_connection(self) -> bool:
        """Test Slack webhook by sending a test message"""
        try:
            success = await self.send_notification(
                message="🔗 QAstra integration connected successfully!",
                channel=self.config.channel
            )
            return success
        except Exception as e:
            raise IntegrationConnectionError(
                f"Failed to connect to Slack: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def get_projects(self) -> List[ProjectData]:
        """Slack webhooks don't have projects - return empty list"""
        return []
    
    async def send_notification(
        self,
        message: str,
        channel: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """Send a message to Slack via webhook"""
        payload = {"text": message}
        
        if channel or self.config.channel:
            payload["channel"] = channel or self.config.channel
        
        if attachments:
            payload["attachments"] = attachments
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code == 403:
                    raise IntegrationAuthError(
                        "Invalid Slack webhook URL",
                        integration_type=self.integration_type
                    )
                
                return response.status_code == 200
        except IntegrationAuthError:
            raise
        except Exception as e:
            raise IntegrationConnectionError(
                f"Failed to send Slack message: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def send_test_run_notification(
        self,
        project_name: str,
        run_id: int,
        status: str,
        passed: int,
        failed: int,
        skipped: int,
        duration_seconds: int,
        url: Optional[str] = None,
    ) -> bool:
        """Send test run result notification with rich formatting"""
        # Check notification settings
        if not self.config.notify_on_test_complete:
            return True
        
        if self.config.notify_on_failure_only and status == "passed":
            return True
        
        emoji = "✅" if status == "passed" else "❌"
        color = "#36a64f" if status == "passed" else "#ff0000"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Test Run Completed",
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Project:*\n{project_name}"},
                    {"type": "mrkdwn", "text": f"*Run ID:*\n{run_id}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{status.upper()}"},
                    {"type": "mrkdwn", "text": f"*Duration:*\n{duration_seconds}s"},
                ]
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Passed:*\n{passed}"},
                    {"type": "mrkdwn", "text": f"*Failed:*\n{failed}"},
                    {"type": "mrkdwn", "text": f"*Skipped:*\n{skipped}"},
                ]
            },
        ]
        
        if url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Results"},
                        "url": url,
                    }
                ]
            })
        
        text = f"Test run #{run_id} for {project_name}: {status}"
        
        payload = {
            "text": text,
            "blocks": blocks,
            "attachments": [{"color": color, "blocks": []}]
        }
        
        if self.config.channel:
            payload["channel"] = self.config.channel
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception:
            return False
