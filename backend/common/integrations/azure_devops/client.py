"""
Azure DevOps Integration Client

Implements ProjectManagementIntegration interface for Azure DevOps.
"""

from typing import List, Optional, Type
from datetime import datetime
import base64
import re
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
from .config import AzureDevOpsConfig


class AzureDevOpsIntegration(ProjectManagementIntegration):
    """
    Azure DevOps integration using the REST API.
    """
    
    integration_type = "azure_devops"
    category = "project_management"
    display_name = "Azure DevOps"
    icon = "🔷"
    
    config: AzureDevOpsConfig
    
    @classmethod
    def get_config_schema(cls) -> Type[BaseIntegrationConfig]:
        return AzureDevOpsConfig
    
    def _get_headers(self) -> dict:
        """Get API headers with Basic auth"""
        token = base64.b64encode(f":{self.config.personal_access_token}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
    
    async def _request(
        self,
        method: str,
        url: str,
        json: dict = None,
        params: dict = None,
    ) -> dict:
        """Make a request to Azure DevOps API"""
        if params is None:
            params = {}
        params["api-version"] = "7.1"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json,
                params=params,
                timeout=30.0,
            )
            
            if response.status_code in [401, 203]:
                raise IntegrationAuthError(
                    "Invalid Azure DevOps PAT",
                    integration_type=self.integration_type
                )
            
            response.raise_for_status()
            return response.json()
    
    async def test_connection(self) -> bool:
        """Test Azure DevOps credentials by fetching projects"""
        try:
            url = f"{self.config.organization_url.rstrip('/')}/_apis/projects"
            await self._request("GET", url)
            return True
        except IntegrationAuthError:
            raise
        except Exception as e:
            raise IntegrationConnectionError(
                f"Failed to connect to Azure DevOps: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def get_projects(self) -> List[ProjectData]:
        """Fetch all accessible Azure DevOps projects"""
        try:
            url = f"{self.config.organization_url.rstrip('/')}/_apis/projects"
            data = await self._request("GET", url)
            return [
                ProjectData(
                    key=p["name"],
                    name=p["name"],
                    description=p.get("description")
                )
                for p in data.get("value", [])
            ]
        except IntegrationAuthError:
            raise
        except Exception as e:
            raise IntegrationConnectionError(
                f"Failed to fetch Azure DevOps projects: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def fetch_user_stories(
        self,
        project_key: str,
        issue_types: Optional[List[str]] = None,
        updated_since: Optional[datetime] = None
    ) -> List[UserStoryData]:
        """Fetch work items from Azure DevOps project using WIQL"""
        try:
            types = issue_types or self.config.work_item_types
            type_clause = " OR ".join([f"[System.WorkItemType] = '{t}'" for t in types])
            
            wiql = f"""
                SELECT [System.Id], [System.Title], [System.State]
                FROM WorkItems
                WHERE [System.TeamProject] = '{project_key}'
                AND ({type_clause})
            """
            
            if updated_since:
                wiql += f" AND [System.ChangedDate] >= '{updated_since.strftime('%Y-%m-%d')}'"
            
            if self.config.area_path:
                wiql += f" AND [System.AreaPath] UNDER '{self.config.area_path}'"
            
            wiql += " ORDER BY [System.ChangedDate] DESC"
            
            url = f"{self.config.organization_url.rstrip('/')}/{project_key}/_apis/wit/wiql"
            result = await self._request("POST", url, json={"query": wiql})
            
            work_item_ids = [item["id"] for item in result.get("workItems", [])]
            
            if not work_item_ids:
                return []
            
            # Fetch work item details in batches
            stories = []
            batch_size = 200
            for i in range(0, len(work_item_ids), batch_size):
                batch_ids = work_item_ids[i:i + batch_size]
                ids_param = ",".join(map(str, batch_ids))
                url = f"{self.config.organization_url.rstrip('/')}/_apis/wit/workitems"
                params = {
                    "ids": ids_param,
                    "fields": "System.Id,System.Title,System.Description,System.State,Microsoft.VSTS.Common.Priority,System.AssignedTo,System.CreatedBy,System.CreatedDate,System.ChangedDate,Microsoft.VSTS.Scheduling.StoryPoints,System.Tags"
                }
                data = await self._request("GET", url, params=params)
                
                for item in data.get("value", []):
                    stories.append(self._map_work_item_to_user_story(item, project_key))
            
            return stories
            
        except IntegrationAuthError:
            raise
        except Exception as e:
            raise IntegrationSyncError(
                f"Failed to fetch work items from Azure DevOps: {str(e)}",
                integration_type=self.integration_type
            )
    
    def _map_work_item_to_user_story(self, item: dict, project_key: str) -> UserStoryData:
        """Map an Azure DevOps work item to standardized UserStoryData"""
        fields = item.get("fields", {})
        
        created_at = None
        updated_at = None
        if fields.get("System.CreatedDate"):
            created_at = datetime.fromisoformat(fields["System.CreatedDate"].replace("Z", "+00:00"))
        if fields.get("System.ChangedDate"):
            updated_at = datetime.fromisoformat(fields["System.ChangedDate"].replace("Z", "+00:00"))
        
        labels = []
        if fields.get("System.Tags"):
            labels = [t.strip() for t in fields["System.Tags"].split(";")]
        
        priority_map = {1: "critical", 2: "high", 3: "medium", 4: "low"}
        priority = priority_map.get(fields.get("Microsoft.VSTS.Common.Priority"), "medium")
        
        # Map work item type to item_type
        work_item_type = fields.get("System.WorkItemType", "").lower()
        item_type_map = {
            "user story": "story",
            "bug": "bug",
            "task": "task",
            "epic": "epic",
            "feature": "feature",
        }
        item_type = item_type_map.get(work_item_type, "story")
        
        # Get parent link
        parent_key = None
        relations = item.get("relations", [])
        for rel in relations:
            if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
                # Extract parent ID from URL
                parent_url = rel.get("url", "")
                if parent_url:
                    parent_id = parent_url.split("/")[-1]
                    parent_key = f"{project_key}-{parent_id}"
                break
        
        return UserStoryData(
            external_id=str(item["id"]),
            external_key=f"{project_key}-{item['id']}",
            title=fields.get("System.Title", ""),
            description=self._strip_html(fields.get("System.Description", "")),
            status=fields.get("System.State", "New"),
            priority=priority,
            item_type=item_type,
            parent_key=parent_key,
            story_points=fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
            assignee=fields.get("System.AssignedTo", {}).get("displayName") if isinstance(fields.get("System.AssignedTo"), dict) else None,
            reporter=fields.get("System.CreatedBy", {}).get("displayName") if isinstance(fields.get("System.CreatedBy"), dict) else None,
            labels=labels,
            created_at=created_at,
            updated_at=updated_at,
            external_url=f"{self.config.organization_url}/{project_key}/_workitems/edit/{item['id']}"
        )
    
    def _strip_html(self, html: str) -> str:
        """Remove HTML tags from description"""
        if not html:
            return ""
        clean = re.sub(r'<[^>]+>', '', html)
        return clean.strip()
    
    async def sync_test_result(self, issue_key: str, result: TestResultData) -> bool:
        """Add test result as a comment on the work item"""
        if not self.config.sync_test_results:
            return True
        
        try:
            work_item_id = issue_key.split("-")[-1]
            
            status_emoji = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}.get(result.status.lower(), "❓")
            
            comment = f"""<div>
<strong>{status_emoji} QAstra Test Result</strong><br/>
<strong>Test Case:</strong> {result.test_case_name}<br/>
<strong>Status:</strong> {result.status.upper()}<br/>
<strong>Duration:</strong> {result.duration_ms}ms<br/>
<strong>Executed:</strong> {result.executed_at.strftime("%Y-%m-%d %H:%M:%S")}<br/>
"""
            if result.error_message:
                comment += f"<strong>Error:</strong><pre>{result.error_message}</pre>"
            comment += "</div>"
            
            url = f"{self.config.organization_url.rstrip('/')}/_apis/wit/workitems/{work_item_id}/comments"
            await self._request("POST", url, json={"text": comment})
            return True
            
        except Exception as e:
            raise IntegrationSyncError(
                f"Failed to sync test result to Azure DevOps: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def get_issue(self, issue_key: str) -> Optional[UserStoryData]:
        """Get a single work item by ID"""
        try:
            parts = issue_key.split("-")
            work_item_id = parts[-1]
            project_key = "-".join(parts[:-1]) if len(parts) > 1 else self.config.project_name
            
            url = f"{self.config.organization_url.rstrip('/')}/_apis/wit/workitems/{work_item_id}"
            data = await self._request("GET", url)
            return self._map_work_item_to_user_story(data, project_key or "")
        except Exception:
            return None
