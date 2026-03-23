"""
Redmine Integration Client

Implements ProjectManagementIntegration interface for Redmine.
"""

from typing import List, Optional, Type
from datetime import datetime
import httpx

from ..base import (
    ProjectManagementIntegration,
    BaseIntegrationConfig,
    UserStoryData,
    ProjectData,
    TestResultData,
)
from ..exceptions import (
    IntegrationConnectionError,
    IntegrationAuthError,
    IntegrationSyncError,
)
from .config import RedmineConfig


class RedmineIntegration(ProjectManagementIntegration):
    """
    Redmine integration using the REST API.
    """
    
    integration_type = "redmine"
    category = "project_management"
    display_name = "Redmine"
    icon = "🔴"
    
    config: RedmineConfig
    
    @classmethod
    def get_config_schema(cls) -> Type[BaseIntegrationConfig]:
        return RedmineConfig
    
    def _get_headers(self) -> dict:
        """Get API headers"""
        return {
            "X-Redmine-API-Key": self.config.api_key,
            "Content-Type": "application/json",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict = None,
        params: dict = None,
    ) -> dict:
        """Make a request to Redmine API"""
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json,
                params=params,
                timeout=30.0,
            )
            
            if response.status_code == 401:
                raise IntegrationAuthError(
                    "Invalid Redmine API key",
                    integration_type=self.integration_type
                )
            
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> bool:
        """Test Redmine credentials by fetching current user"""
        try:
            await self._request("GET", "users/current")
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise IntegrationAuthError(
                    "Invalid Redmine API key",
                    integration_type=self.integration_type
                )
            raise IntegrationConnectionError(
                f"Failed to connect to Redmine: {str(e)}",
                integration_type=self.integration_type
            )
        except Exception as e:
            raise IntegrationConnectionError(
                f"Failed to connect to Redmine: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def get_projects(self) -> List[ProjectData]:
        """Fetch all accessible Redmine projects"""
        try:
            data = await self._request("GET", "projects", params={"limit": 100})
            return [
                ProjectData(
                    key=str(p["identifier"]),
                    name=p["name"],
                    description=p.get("description")
                )
                for p in data.get("projects", [])
            ]
        except Exception as e:
            raise IntegrationConnectionError(
                f"Failed to fetch Redmine projects: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def fetch_user_stories(
        self,
        project_key: str,
        issue_types: Optional[List[str]] = None,
        updated_since: Optional[datetime] = None
    ) -> List[UserStoryData]:
        """Fetch issues from Redmine project"""
        try:
            params = {
                "project_id": project_key,
                "limit": 100,
                "status_id": "*",  # All statuses
            }
            
            if self.config.tracker_ids:
                params["tracker_id"] = ",".join(map(str, self.config.tracker_ids))
            
            if updated_since:
                params["updated_on"] = f">={updated_since.strftime('%Y-%m-%d')}"
            
            data = await self._request("GET", "issues", params=params)
            
            return [self._map_issue_to_user_story(issue) for issue in data.get("issues", [])]
            
        except Exception as e:
            raise IntegrationSyncError(
                f"Failed to fetch issues from Redmine: {str(e)}",
                integration_type=self.integration_type
            )
    
    def _map_issue_to_user_story(self, issue: dict) -> UserStoryData:
        """Map a Redmine issue to standardized UserStoryData"""
        # Map tracker to item_type
        tracker_name = issue.get("tracker", {}).get("name", "").lower()
        item_type_map = {
            "bug": "bug",
            "feature": "feature",
            "support": "task",
            "task": "task",
            "user story": "story",
            "epic": "epic",
        }
        item_type = item_type_map.get(tracker_name, "story")
        
        # Get parent issue key
        parent_key = None
        if issue.get("parent"):
            parent_key = f"#{issue['parent']['id']}"
        
        return UserStoryData(
            external_id=str(issue["id"]),
            external_key=f"#{issue['id']}",
            title=issue["subject"],
            description=issue.get("description"),
            status=issue.get("status", {}).get("name", "Unknown"),
            priority=issue.get("priority", {}).get("name"),
            item_type=item_type,
            parent_key=parent_key,
            story_points=issue.get("estimated_hours"),
            assignee=issue.get("assigned_to", {}).get("name"),
            reporter=issue.get("author", {}).get("name"),
            labels=[],
            created_at=datetime.fromisoformat(issue["created_on"].replace("Z", "+00:00")) if issue.get("created_on") else None,
            updated_at=datetime.fromisoformat(issue["updated_on"].replace("Z", "+00:00")) if issue.get("updated_on") else None,
            external_url=f"{self.config.base_url}/issues/{issue['id']}"
        )
    
    async def sync_test_result(
        self,
        issue_key: str,
        result: TestResultData
    ) -> bool:
        """Post test result as a note on the Redmine issue"""
        if not self.config.sync_notes:
            return True
        
        try:
            issue_id = issue_key.replace("#", "")
            
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(result.status.lower(), "❓")
            
            note = f"""
{status_emoji} **QAstra Test Result**

**Test Case:** {result.test_case_name}
**Status:** {result.status.upper()}
**Duration:** {result.duration_ms}ms
**Executed:** {result.executed_at.strftime("%Y-%m-%d %H:%M:%S")}
"""
            
            if result.error_message:
                note += f"\n**Error:**\n<pre>\n{result.error_message}\n</pre>"
            
            await self._request(
                "PUT",
                f"issues/{issue_id}",
                json={"issue": {"notes": note}}
            )
            return True
            
        except Exception as e:
            raise IntegrationSyncError(
                f"Failed to add note to {issue_key}: {str(e)}",
                integration_type=self.integration_type
            )
