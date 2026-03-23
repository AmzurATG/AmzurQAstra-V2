"""
Notification Service
"""
from typing import Optional, List
import httpx
from config import settings


class NotificationService:
    """Service for sending notifications."""
    
    async def send_slack_message(
        self,
        message: str,
        channel: Optional[str] = None,
        blocks: Optional[List[dict]] = None,
    ) -> bool:
        """Send a message to Slack."""
        if not settings.SLACK_WEBHOOK_URL:
            return False
        
        payload = {"text": message}
        if channel:
            payload["channel"] = channel
        if blocks:
            payload["blocks"] = blocks
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                )
                return response.status_code == 200
        except Exception:
            return False
    
    async def send_test_run_notification(
        self,
        project_name: str,
        test_run_id: int,
        status: str,
        passed: int,
        failed: int,
        total: int,
    ) -> bool:
        """Send test run completion notification."""
        emoji = "✅" if status == "passed" else "❌"
        message = (
            f"{emoji} *Test Run Completed*\n"
            f"Project: {project_name}\n"
            f"Run ID: {test_run_id}\n"
            f"Status: {status}\n"
            f"Results: {passed}/{total} passed, {failed}/{total} failed"
        )
        return await self.send_slack_message(message)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None,
    ) -> bool:
        """Send an email. (TODO: Implement with actual email service)"""
        # Placeholder for email implementation
        # Could use SendGrid, AWS SES, etc.
        return True
