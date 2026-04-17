"""
Jira Integration Client

Implements ProjectManagementIntegration interface for Jira Cloud/Server.
"""

from typing import List, Optional, Type
from datetime import datetime
import asyncio
from functools import partial
from urllib.parse import urlparse
import httpx
from base64 import b64encode

from jira import JIRA
from jira.exceptions import JIRAError

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
from .config import JiraConfig


def _friendly_jira_connect_error(exc: Exception) -> str:
    """Short, user-facing message — avoid raw library / stack traces in the UI."""
    et = type(exc).__name__
    if et in ("InvalidURL", "MissingSchema", "InvalidSchema"):
        return "Use a full URL like https://yourcompany.atlassian.net"
    if et in (
        "ConnectionError",
        "ConnectTimeout",
        "Timeout",
        "ReadTimeout",
        "ProxyError",
    ):
        return "Could not reach that server. Check the Jira URL and your network."
    if et == "SSLError":
        return "Secure connection failed. Use https:// and your real Jira site URL."
    msg = str(exc).lower()
    if "nodename nor servname" in msg or "name or service not known" in msg or "getaddrinfo failed" in msg:
        return "That site address could not be found. Check spelling (e.g. yourcompany.atlassian.net)."
    if "connection refused" in msg:
        return "Connection refused. Check the URL and that Jira is reachable."
    if "timed out" in msg or "timeout" in msg:
        return "The request timed out. Check the URL and try again."
    if "certificate" in msg or "ssl" in msg:
        return "SSL error — use https:// with a valid Jira URL."
    return "Could not connect to Jira. Check the site URL, email, and API token."


class JiraIntegration(ProjectManagementIntegration):
    """
    Jira integration using the official jira-python library.
    
    Supports both Jira Cloud and Jira Server/Data Center.
    """
    
    integration_type = "jira"
    category = "project_management"
    display_name = "Jira"
    icon = "🎫"
    
    config: JiraConfig
    
    @classmethod
    def get_config_schema(cls) -> Type[BaseIntegrationConfig]:
        return JiraConfig

    def _ensure_valid_jira_url(self) -> None:
        """Normalize base_url and reject obviously invalid values before HTTP calls."""
        raw = (self.config.base_url or "").strip()
        if not raw:
            raise IntegrationConnectionError(
                "Enter your Jira site URL.",
                integration_type=self.integration_type,
            )
        if not raw.startswith(("http://", "https://")):
            raise IntegrationConnectionError(
                "Start with https:// — for example https://yourcompany.atlassian.net",
                integration_type=self.integration_type,
            )
        parsed = urlparse(raw)
        if not parsed.netloc:
            raise IntegrationConnectionError(
                "That URL looks incomplete. Example: https://yourcompany.atlassian.net",
                integration_type=self.integration_type,
            )
        self.config.base_url = raw.rstrip("/")
    
    def _get_client(self) -> JIRA:
        """Create and return a Jira client instance"""
        self._ensure_valid_jira_url()
        if self._client is None:
            self._client = JIRA(
                server=self.config.base_url.rstrip("/"),
                basic_auth=(self.config.email, self.config.api_token),
                max_retries=3,
            )
        return self._client
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous Jira API calls in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))
    
    async def test_connection(self) -> bool:
        """Test Jira credentials by fetching current user"""
        try:
            client = self._get_client()
            await self._run_sync(client.myself)
            return True
        except IntegrationConnectionError:
            raise
        except IntegrationAuthError:
            raise
        except JIRAError as e:
            if e.status_code == 401:
                raise IntegrationAuthError(
                    "Invalid email or API token.",
                    integration_type=self.integration_type
                )
            elif e.status_code == 403:
                raise IntegrationAuthError(
                    "Access denied — your token may need more Jira permissions.",
                    integration_type=self.integration_type
                )
            elif e.status_code == 404:
                raise IntegrationConnectionError(
                    "Jira did not respond at that URL. Confirm your Cloud/Server site address.",
                    integration_type=self.integration_type
                )
            else:
                raise IntegrationConnectionError(
                    "Could not reach Jira. Check the site URL (https://…atlassian.net).",
                    integration_type=self.integration_type
                )
        except Exception as e:
            raise IntegrationConnectionError(
                _friendly_jira_connect_error(e),
                integration_type=self.integration_type
            )
    
    async def get_projects(self) -> List[ProjectData]:
        """Fetch all accessible Jira projects"""
        try:
            client = self._get_client()
            projects = await self._run_sync(client.projects)
            return [
                ProjectData(
                    key=p.key,
                    name=p.name,
                    description=getattr(p, "description", None)
                )
                for p in projects
            ]
        except JIRAError as e:
            raise IntegrationConnectionError(
                f"Failed to fetch Jira projects: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def get_sprints(self, board_id: Optional[int] = None) -> List[dict]:
        """
        Fetch sprints from Jira using the Agile API.
        
        Args:
            board_id: Specific board ID, or if None fetches from config or discovers boards
            
        Returns:
            List of sprint dictionaries with id, name, state, startDate, endDate
        """
        try:
            base_url = self.config.base_url.rstrip("/")
            
            # Validate URL format
            if not base_url.startswith(("http://", "https://")):
                print(f"Warning: Invalid Jira URL format: {base_url}")
                return []
            
            auth_str = f"{self.config.email}:{self.config.api_token}"
            auth_bytes = b64encode(auth_str.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_bytes}",
                "Accept": "application/json",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # First, get boards for the project
                if not board_id:
                    project_key = self.config.project_key
                    boards_url = f"{base_url}/rest/agile/1.0/board"
                    params = {"projectKeyOrId": project_key} if project_key else {}
                    
                    try:
                        response = await client.get(boards_url, headers=headers, params=params)
                    except httpx.ConnectError as e:
                        print(f"Warning: Cannot connect to Jira at {base_url}: {str(e)}")
                        return []
                    
                    if response.status_code != 200:
                        # Agile API might not be available, return empty
                        return []
                    
                    boards_data = response.json()
                    boards = boards_data.get("values", [])
                    
                    if not boards:
                        return []
                    
                    # Use first board (usually Scrum board)
                    board_id = boards[0].get("id")
                
                # Fetch sprints for the board
                sprints_url = f"{base_url}/rest/agile/1.0/board/{board_id}/sprint"
                all_sprints = []
                start_at = 0
                
                while True:
                    params = {"startAt": start_at, "maxResults": 50}
                    
                    try:
                        response = await client.get(sprints_url, headers=headers, params=params)
                    except httpx.ConnectError as e:
                        print(f"Warning: Cannot connect to Jira for sprints: {str(e)}")
                        break
                    
                    if response.status_code != 200:
                        break
                    
                    data = response.json()
                    sprints = data.get("values", [])
                    all_sprints.extend(sprints)
                    
                    if data.get("isLast", True) or len(sprints) == 0:
                        break
                    
                    start_at += len(sprints)
                
                # Return sorted by state (active first, then future, then closed)
                state_order = {"active": 0, "future": 1, "closed": 2}
                all_sprints.sort(key=lambda s: (state_order.get(s.get("state", ""), 9), s.get("name", "")))
                
                return all_sprints
                
        except httpx.ConnectError as e:
            # Network/DNS errors - log the URL being accessed for debugging
            print(f"Warning: Failed to connect to Jira ({self.config.base_url}): {str(e)}")
            return []
        except Exception as e:
            # Sprint API errors should not break the integration
            print(f"Warning: Failed to fetch sprints: {str(e)}")
            return []
    
    async def fetch_user_stories(
        self,
        project_key: str,
        issue_types: Optional[List[str]] = None,
        updated_since: Optional[datetime] = None,
        sprint_id: Optional[int] = None,
        sprint_ids: Optional[List[int]] = None,
    ) -> List[UserStoryData]:
        """
        Fetch issues from Jira project using the new /search/jql API.
        
        Args:
            project_key: Jira project key (e.g., "PROJ")
            issue_types: Filter by issue types, defaults to config value
            updated_since: Only fetch issues updated after this time
            sprint_id: Deprecated; use sprint_ids with one element.
            sprint_ids: Filter by one or more sprint IDs (optional). Omitted/empty = all sprints.
        """
        try:
            # Build JQL query
            if self.config.jql_filter:
                jql = self.config.jql_filter
            else:
                types = issue_types or self.config.issue_types
                types_str = ", ".join([f'"{t}"' for t in types])
                jql = f"project = {project_key} AND issuetype IN ({types_str})"
            
            # Add sprint filter (single sprint or sprint in (...))
            effective_sprint_ids: Optional[List[int]] = None
            if sprint_ids:
                effective_sprint_ids = list(dict.fromkeys(sprint_ids))
            elif sprint_id is not None:
                effective_sprint_ids = [sprint_id]
            if effective_sprint_ids:
                if len(effective_sprint_ids) == 1:
                    jql += f" AND sprint = {effective_sprint_ids[0]}"
                else:
                    ids_jql = ", ".join(str(sid) for sid in effective_sprint_ids)
                    jql += f" AND sprint in ({ids_jql})"
            
            if updated_since:
                jql += f' AND updated >= "{updated_since.strftime("%Y-%m-%d %H:%M")}"'
            
            jql += " ORDER BY updated DESC"
            
            # Use the new /search/jql endpoint (required since Jira deprecated /search)
            # Include sprint field (customfield_10020 is common, also try customfield_10007)
            fields = "summary,description,status,priority,assignee,reporter,labels,customfield_10016,customfield_10014,customfield_10024,customfield_10002,customfield_10020,customfield_10007,sprint,issuetype,created,updated,parent"
            
            # Build auth header
            auth_str = f"{self.config.email}:{self.config.api_token}"
            auth_bytes = b64encode(auth_str.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_bytes}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            base_url = self.config.base_url.rstrip("/")
            url = f"{base_url}/rest/api/3/search/jql"
            
            all_issues = []
            start_at = 0
            max_results = 100
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                while True:
                    params = {
                        "jql": jql,
                        "fields": fields,
                        "startAt": start_at,
                        "maxResults": max_results
                    }
                    
                    response = await client.get(url, headers=headers, params=params)
                    
                    if response.status_code == 401:
                        raise IntegrationAuthError(
                            "Invalid Jira credentials",
                            integration_type=self.integration_type
                        )
                    
                    if response.status_code != 200:
                        error_text = response.text[:500]
                        raise IntegrationSyncError(
                            f"Jira API error ({response.status_code}): {error_text}",
                            integration_type=self.integration_type
                        )
                    
                    data = response.json()
                    issues = data.get("issues", [])
                    all_issues.extend(issues)
                    
                    # Check if we have more pages
                    total = data.get("total", 0)
                    if start_at + len(issues) >= total or len(issues) == 0:
                        break
                    
                    start_at += len(issues)
                    
                    # Safety limit
                    if len(all_issues) >= 500:
                        break
            
            return [self._map_issue_dict_to_user_story(issue) for issue in all_issues]
            
        except (IntegrationAuthError, IntegrationSyncError):
            raise
        except Exception as e:
            raise IntegrationSyncError(
                f"Failed to fetch issues from Jira: {str(e)}",
                integration_type=self.integration_type
            )
    
    def _map_issue_dict_to_user_story(self, issue: dict) -> UserStoryData:
        """Map a Jira issue dict (from REST API) to standardized UserStoryData"""
        fields = issue.get("fields", {})
        
        # Get story points (common custom field names)
        story_points = None
        for field_name in ["customfield_10016", "customfield_10024", "customfield_10002"]:
            value = fields.get(field_name)
            if value is not None:
                story_points = int(value) if isinstance(value, (int, float)) else None
                break
        
        # Extract sprint information (common custom field names for sprint)
        sprint_id = None
        sprint_name = None
        for field_name in ["sprint", "customfield_10020", "customfield_10007"]:
            sprint_value = fields.get(field_name)
            if sprint_value:
                # Sprint can be a list (issue can be in multiple sprints)
                if isinstance(sprint_value, list) and len(sprint_value) > 0:
                    # Get the most recent/active sprint (usually the last one)
                    active_sprint = None
                    for s in sprint_value:
                        if isinstance(s, dict):
                            if s.get("state") == "active":
                                active_sprint = s
                                break
                    # If no active sprint, take the last one
                    if not active_sprint:
                        active_sprint = sprint_value[-1] if isinstance(sprint_value[-1], dict) else None
                    
                    if active_sprint:
                        sprint_id = str(active_sprint.get("id", ""))
                        sprint_name = active_sprint.get("name", "")
                elif isinstance(sprint_value, dict):
                    sprint_id = str(sprint_value.get("id", ""))
                    sprint_name = sprint_value.get("name", "")
                
                if sprint_id:
                    break
        
        # Map issue type to item_type
        issue_type_obj = fields.get("issuetype", {})
        issue_type_str = (issue_type_obj.get("name", "story") if isinstance(issue_type_obj, dict) else "story").lower()
        # Normalize subtask variants
        if issue_type_str in ["sub-task", "subtask"]:
            item_type = "subtask"
        elif issue_type_str in ["epic", "story", "bug", "task"]:
            item_type = issue_type_str
        else:
            item_type = "story"
        
        # Get parent key (for stories under epics, or subtasks under stories)
        parent_key = None
        parent = fields.get("parent")
        if parent and isinstance(parent, dict):
            parent_key = parent.get("key")
        elif not parent_key:
            # Epic link field
            parent_key = fields.get("customfield_10014")
        
        # Extract nested values
        status = fields.get("status", {})
        status_name = status.get("name", "Unknown") if isinstance(status, dict) else str(status)
        
        priority = fields.get("priority", {})
        priority_name = priority.get("name") if isinstance(priority, dict) else None
        
        assignee = fields.get("assignee", {})
        assignee_name = assignee.get("displayName") if isinstance(assignee, dict) else None
        
        reporter = fields.get("reporter", {})
        reporter_name = reporter.get("displayName") if isinstance(reporter, dict) else None
        
        created = fields.get("created")
        updated = fields.get("updated")
        
        return UserStoryData(
            external_id=issue.get("id"),
            external_key=issue.get("key"),
            title=fields.get("summary", "Untitled"),
            description=self._extract_description(fields.get("description")),
            status=status_name,
            priority=priority_name,
            item_type=item_type,
            parent_key=parent_key,
            story_points=story_points,
            assignee=assignee_name,
            reporter=reporter_name,
            labels=fields.get("labels", []) if self.config.sync_labels else [],
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            created_at=datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None,
            updated_at=datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else None,
            external_url=f"{self.config.base_url}/browse/{issue.get('key')}"
        )
    
    def _extract_description(self, desc) -> Optional[str]:
        """Extract plain text from Jira's ADF (Atlassian Document Format) or string"""
        if desc is None:
            return None
        if isinstance(desc, str):
            return desc
        if isinstance(desc, dict):
            # ADF format - extract text content
            return self._adf_to_text(desc)
        return str(desc)
    
    def _adf_to_text(self, adf: dict) -> str:
        """Convert Atlassian Document Format to plain text"""
        text_parts = []
        
        def extract_text(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    text_parts.append(node.get("text", ""))
                for child in node.get("content", []):
                    extract_text(child)
            elif isinstance(node, list):
                for item in node:
                    extract_text(item)
        
        extract_text(adf)
        return " ".join(text_parts)
    
    async def get_issue(self, issue_key: str) -> Optional[UserStoryData]:
        """Fetch a single Jira issue by key"""
        try:
            client = self._get_client()
            issue = await self._run_sync(client.issue, issue_key)
            return self._map_issue_to_user_story(issue)
        except JIRAError:
            return None
    
    async def sync_test_result(
        self,
        issue_key: str,
        result: TestResultData
    ) -> bool:
        """Post test result as a comment on the Jira issue"""
        if not self.config.sync_comments:
            return True
        
        try:
            client = self._get_client()
            
            # Format the comment
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️"
            }.get(result.status.lower(), "❓")
            
            comment = f"""
{status_emoji} *QAstra Test Result*

*Test Case:* {result.test_case_name}
*Status:* {result.status.upper()}
*Duration:* {result.duration_ms}ms
*Executed:* {result.executed_at.strftime("%Y-%m-%d %H:%M:%S")}
"""
            
            if result.error_message:
                comment += f"\n*Error:*\n{{code}}\n{result.error_message}\n{{code}}"
            
            if result.screenshot_url:
                comment += f"\n[View Screenshot|{result.screenshot_url}]"
            
            await self._run_sync(client.add_comment, issue_key, comment)
            return True
            
        except JIRAError as e:
            raise IntegrationSyncError(
                f"Failed to add comment to {issue_key}: {str(e)}",
                integration_type=self.integration_type
            )
    
    async def get_issue_types(self, project_key: str) -> List[dict]:
        """Get available issue types for a project"""
        try:
            client = self._get_client()
            project = await self._run_sync(client.project, project_key)
            issue_types = await self._run_sync(lambda: project.issueTypes)
            return [
                {"id": it.id, "name": it.name, "description": getattr(it, "description", "")}
                for it in issue_types
            ]
        except JIRAError as e:
            raise IntegrationConnectionError(
                f"Failed to fetch issue types: {str(e)}",
                integration_type=self.integration_type
            )
