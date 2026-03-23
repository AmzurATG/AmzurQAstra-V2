"""
Integration Configuration Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.integrations.jira.client import JiraIntegration
from common.integrations.azure_devops.client import AzureDevOpsIntegration


router = APIRouter()


class JiraConfig(BaseModel):
    """Jira configuration."""
    base_url: str
    email: str
    api_token: str
    project_key: Optional[str] = None


class AzureDevOpsConfig(BaseModel):
    """Azure DevOps configuration."""
    org_url: str
    pat: str
    project: Optional[str] = None


class IntegrationTestResult(BaseModel):
    """Integration test result."""
    success: bool
    message: str


@router.post("/jira/test", response_model=IntegrationTestResult)
async def test_jira_connection(
    config: JiraConfig,
    current_user: User = Depends(get_current_active_user),
):
    """Test Jira connection with provided credentials."""
    try:
        integration = JiraIntegration(config={
            "base_url": config.base_url,
            "email": config.email,
            "api_token": config.api_token,
        })
        
        await integration.test_connection()
        
        if config.project_key:
            projects = await integration.get_projects()
            return IntegrationTestResult(
                success=True,
                message=f"Successfully connected to Jira. Found {len(projects)} accessible projects.",
            )
        else:
            return IntegrationTestResult(
                success=True,
                message="Jira credentials are valid. Provide a project key to verify project access.",
            )
    except Exception as e:
        return IntegrationTestResult(
            success=False,
            message=f"Failed to connect to Jira: {str(e)}",
        )


@router.post("/azure-devops/test", response_model=IntegrationTestResult)
async def test_azure_devops_connection(
    config: AzureDevOpsConfig,
    current_user: User = Depends(get_current_active_user),
):
    """Test Azure DevOps connection with provided credentials."""
    try:
        integration = AzureDevOpsIntegration(config={
            "organization_url": config.org_url,
            "personal_access_token": config.pat,
            "project": config.project,
        })
        
        await integration.test_connection()
        
        if config.project:
            projects = await integration.get_projects()
            return IntegrationTestResult(
                success=True,
                message=f"Successfully connected to Azure DevOps. Found {len(projects)} projects.",
            )
        else:
            return IntegrationTestResult(
                success=True,
                message="Azure DevOps credentials appear valid. Provide a project to verify access.",
            )
    except Exception as e:
        return IntegrationTestResult(
            success=False,
            message=f"Failed to connect to Azure DevOps: {str(e)}",
        )


@router.get("/jira/projects")
async def list_jira_projects(
    current_user: User = Depends(get_current_active_user),
):
    """List available Jira projects."""
    client = JiraClient()
    if not client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jira is not configured",
        )
    
    # TODO: Implement project listing
    return {"message": "Not implemented yet"}


@router.get("/azure-devops/projects")
async def list_azure_devops_projects(
    current_user: User = Depends(get_current_active_user),
):
    """List available Azure DevOps projects."""
    client = AzureDevOpsClient()
    if not client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Azure DevOps is not configured",
        )
    
    # TODO: Implement project listing
    return {"message": "Not implemented yet"}
