"""
MCP Client - Communicates with the MCP Server for Playwright operations
"""
from typing import Optional, Dict, Any, List
import httpx

from config import settings
from common.utils.logger import logger


class MCPClient:
    """Client for communicating with the MCP Server."""
    
    def __init__(self, base_url: Optional[str] = None, headless: bool = False):
        self.base_url = (base_url or settings.MCP_SERVER_URL).rstrip("/")
        self.timeout = 30.0  # seconds
        self._session_id: Optional[str] = None
        self._headless = headless
    
    async def _ensure_session(self) -> str:
        """Ensure we have a valid session, create one if needed."""
        if self._session_id:
            # Verify session still exists
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.base_url}/mcp/sessions/{self._session_id}")
                    if response.status_code == 200:
                        return self._session_id
            except Exception:
                pass
        
        # Create new session
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mcp/sessions",
                    json={"browserType": "chromium", "headless": self._headless}
                )
                response.raise_for_status()
                data = response.json()
                self._session_id = data["id"]
                logger.info(f"Created MCP session: {self._session_id} (headless={self._headless})")
                return self._session_id
        except Exception as e:
            logger.error(f"Failed to create MCP session: {e}")
            raise
    
    async def _execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action via MCP server."""
        try:
            session_id = await self._ensure_session()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mcp/execute",
                    json={"sessionId": session_id, "action": action}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"MCP execute failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"MCP error: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_session(self) -> None:
        """Close the current session."""
        if self._session_id:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    await client.delete(f"{self.base_url}/mcp/sessions/{self._session_id}")
                    logger.info(f"Closed MCP session: {self._session_id}")
            except Exception as e:
                logger.warning(f"Failed to close session: {e}")
            finally:
                self._session_id = None
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        return await self._execute({"action": "navigate", "target": url})
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        return await self._execute({"action": "click", "target": selector})
    
    async def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """Fill an input field."""
        return await self._execute({
            "action": "fill",
            "target": selector,
            "value": value,
        })
    
    async def select(self, selector: str, value: str) -> Dict[str, Any]:
        """Select a dropdown option."""
        return await self._execute({
            "action": "select",
            "target": selector,
            "value": value,
        })
    
    async def hover(self, selector: str) -> Dict[str, Any]:
        """Hover over an element."""
        return await self._execute({"action": "hover", "target": selector})
    
    async def screenshot(self, name: str) -> Dict[str, Any]:
        """Take a screenshot."""
        if not self._session_id:
            return {"success": False, "error": "No session"}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mcp/screenshot",
                    json={"sessionId": self._session_id, "fullPage": False}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def wait(self, milliseconds: int) -> Dict[str, Any]:
        """Wait for a specified time."""
        return await self._execute({"action": "wait", "value": str(milliseconds)})
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        """Wait for an element to appear."""
        return await self._execute({
            "action": "waitForSelector",
            "target": selector,
            "timeout": timeout,
        })
    
    async def get_text(self, selector: str) -> Dict[str, Any]:
        """Get text content of an element."""
        return await self._execute({"action": "evaluate", "value": f"document.querySelector('{selector}')?.textContent"})
    
    async def is_visible(self, selector: str) -> bool:
        """Check if an element is visible."""
        try:
            result = await self._execute({"action": "assertVisible", "target": selector})
            return result.get("success", False)
        except Exception:
            return False
    
    async def assert_text(self, selector: str, expected: str) -> Dict[str, Any]:
        """Assert element contains expected text."""
        return await self._execute({
            "action": "assertText",
            "target": selector,
            "value": expected,
        })
    
    async def assert_url(self, expected: str) -> Dict[str, Any]:
        """Assert current URL matches expected."""
        return await self._execute({"action": "assertUrl", "target": expected})
    
    async def get_elements(self) -> Dict[str, Any]:
        """Get visible elements on the current page."""
        return await self._request("GET", "elements")
    
    async def execute_test_case(self, test_case) -> Dict[str, Any]:
        """Execute a complete test case."""
        steps = []
        for step in test_case.steps:
            steps.append({
                "action": step.action.value,
                "target": step.target,
                "value": step.value,
                "expected_result": step.expected_result,
            })
        
        return await self._request("POST", "execute-test-case", {
            "test_case_id": test_case.id,
            "title": test_case.title,
            "steps": steps,
        })
