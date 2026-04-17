"""
Project Integrations API Endpoints

Manages external integrations (Jira, Redmine, Azure DevOps, Slack, etc.) on a per-project basis.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime

from common.db.database import get_db
from common.db.models.user import User
from common.db.models.integration import (
    ProjectIntegration,
    IntegrationType,
    IntegrationCategory,
    SyncStatus,
)
from common.api.deps import get_current_active_user
from common.integrations import get_integration, get_available_integrations
from common.integrations.exceptions import (
    IntegrationError,
    IntegrationConnectionError,
    IntegrationAuthError,
    IntegrationNotFoundError,
)
from common.utils.security import encrypt_config, decrypt_config


router = APIRouter()


# =====================================================
# SCHEMAS
# =====================================================

class IntegrationConfigCreate(BaseModel):
    """Create integration config"""
    integration_type: str = Field(..., description="Integration type (jira, redmine, etc.)")
    name: Optional[str] = Field(None, description="Display name for this integration")
    config: dict = Field(..., description="Type-specific configuration")
    is_enabled: bool = Field(True, description="Whether integration is enabled")


class IntegrationConfigUpdate(BaseModel):
    """Update integration config"""
    name: Optional[str] = None
    config: Optional[dict] = None
    is_enabled: Optional[bool] = None


class IntegrationResponse(BaseModel):
    """Integration response"""
    id: int
    project_id: int
    integration_type: str
    integration_category: str
    name: Optional[str]
    config: Optional[dict] = None  # Config with sensitive fields redacted
    is_enabled: bool
    last_sync_at: Optional[datetime]
    sync_status: str
    last_sync_error: Optional[str]
    items_synced: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Fields that should NEVER be redacted (even if they match sensitive keywords)
NON_SENSITIVE_FIELDS = {
    'project_key',
    'project_name',
    'webhook_key',
    'channel_key',
    'sync_scope',
    'issue_types',
    'sync_comments',
    'sync_labels',
    'jql_filter',
}

# Fields that should ALWAYS be redacted
SENSITIVE_KEYWORDS = ['token', 'password', 'secret', 'api_key', 'pat', 'access_token', 'api_token', 'personal_access_token']


def redact_sensitive_config(config: dict) -> dict:
    """
    Return config with sensitive fields redacted.
    API tokens, passwords, and secrets are replaced with asterisks.
    Project identifiers like project_key are NOT redacted.
    Handles both plain and encrypted (enc: prefixed) values.
    """
    if not config:
        return {}
    
    redacted = {}
    
    for field_name, value in config.items():
        # Skip redaction for explicitly non-sensitive fields
        if field_name.lower() in NON_SENSITIVE_FIELDS:
            redacted[field_name] = value
            continue
        
        # Check if value is encrypted (starts with 'enc:')
        if isinstance(value, str) and value.startswith('enc:'):
            redacted[field_name] = '********'
            continue
            
        # Check if field name contains sensitive keywords
        is_sensitive = any(kw in field_name.lower() for kw in SENSITIVE_KEYWORDS)
        if is_sensitive and value:
            redacted[field_name] = '********'
        else:
            redacted[field_name] = value
    
    return redacted


class IntegrationMetadataResponse(BaseModel):
    """Available integration metadata"""
    type: str
    name: str
    category: str
    icon: str
    description: str
    features: List[str]
    config_fields: List[dict]


class TestConnectionRequest(BaseModel):
    """Test connection request"""
    config: dict


class RemoteProject(BaseModel):
    """Remote project from external tool"""
    key: str
    name: str
    description: Optional[str] = None


class TestConnectionResponse(BaseModel):
    """Test connection response"""
    success: bool
    message: str
    projects: Optional[List[RemoteProject]] = None


class ProjectListResponse(BaseModel):
    """Remote projects list response"""
    projects: List[dict]


# =====================================================
# ENDPOINTS
# =====================================================

@router.get("/available", response_model=List[IntegrationMetadataResponse])
async def list_available_integrations(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """List all available integration types with their metadata and config fields."""
    return get_available_integrations(category)


@router.get("/{project_id}", response_model=List[IntegrationResponse])
async def list_project_integrations(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all integrations configured for a project."""
    result = await db.execute(
        select(ProjectIntegration).where(ProjectIntegration.project_id == project_id)
    )
    integrations = result.scalars().all()
    
    return [
        IntegrationResponse(
            id=i.id,
            project_id=i.project_id,
            integration_type=i.integration_type.value,
            integration_category=i.integration_category.value,
            name=i.name,
            config=redact_sensitive_config(i.config),
            is_enabled=i.is_enabled,
            last_sync_at=i.last_sync_at,
            sync_status=i.sync_status.value,
            last_sync_error=i.last_sync_error,
            items_synced=i.items_synced,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in integrations
    ]


@router.get("/{project_id}/{integration_type}", response_model=IntegrationResponse)
async def get_project_integration(
    project_id: int,
    integration_type: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific integration for a project."""
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {integration_type}"
        )
    
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == int_type
        )
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_type} not configured for this project"
        )
    
    return IntegrationResponse(
        id=integration.id,
        project_id=integration.project_id,
        integration_type=integration.integration_type.value,
        integration_category=integration.integration_category.value,
        name=integration.name,
        config=redact_sensitive_config(integration.config),
        is_enabled=integration.is_enabled,
        last_sync_at=integration.last_sync_at,
        sync_status=integration.sync_status.value,
        last_sync_error=integration.last_sync_error,
        items_synced=integration.items_synced,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.post("/{project_id}", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def create_project_integration(
    project_id: int,
    data: IntegrationConfigCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create/configure an integration for a project."""
    try:
        int_type = IntegrationType(data.integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {data.integration_type}"
        )
    
    # Check if already exists
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == int_type
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integration {data.integration_type} already configured for this project"
        )
    
    # Validate config by creating integration instance
    try:
        integration_instance = get_integration(data.integration_type, data.config)
        category = IntegrationCategory(integration_instance.category)
    except IntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration: {str(e)}"
        )
    
    # Encrypt sensitive config fields before storage
    encrypted_config = encrypt_config(data.config)
    
    # Create integration record
    integration = ProjectIntegration(
        project_id=project_id,
        integration_type=int_type,
        integration_category=category,
        name=data.name,
        config=encrypted_config,
        is_enabled=data.is_enabled,
        configured_by_id=current_user.id,
    )
    
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    
    return IntegrationResponse(
        id=integration.id,
        project_id=integration.project_id,
        integration_type=integration.integration_type.value,
        integration_category=integration.integration_category.value,
        name=integration.name,
        config=redact_sensitive_config(integration.config),
        is_enabled=integration.is_enabled,
        last_sync_at=integration.last_sync_at,
        sync_status=integration.sync_status.value,
        last_sync_error=integration.last_sync_error,
        items_synced=integration.items_synced,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.put("/{project_id}/{integration_type}", response_model=IntegrationResponse)
async def update_project_integration(
    project_id: int,
    integration_type: str,
    data: IntegrationConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an integration configuration."""
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {integration_type}"
        )
    
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == int_type
        )
    )
    integration = result.scalar_one_or_none()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_type} not configured for this project"
        )
    
    # Update fields
    if data.name is not None:
        integration.name = data.name
    if data.is_enabled is not None:
        integration.is_enabled = data.is_enabled
    if data.config is not None:
        # Validate new config
        try:
            get_integration(integration_type, data.config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration: {str(e)}"
            )
        # Encrypt sensitive fields before storage
        integration.config = encrypt_config(data.config)
    
    await db.commit()
    await db.refresh(integration)
    
    return IntegrationResponse(
        id=integration.id,
        project_id=integration.project_id,
        integration_type=integration.integration_type.value,
        integration_category=integration.integration_category.value,
        name=integration.name,
        config=redact_sensitive_config(integration.config),
        is_enabled=integration.is_enabled,
        last_sync_at=integration.last_sync_at,
        sync_status=integration.sync_status.value,
        last_sync_error=integration.last_sync_error,
        items_synced=integration.items_synced,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.delete("/{project_id}/{integration_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_integration(
    project_id: int,
    integration_type: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an integration from a project."""
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {integration_type}"
        )
    
    result = await db.execute(
        delete(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == int_type
        )
    )
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_type} not configured for this project"
        )
    
    await db.commit()


@router.post("/{project_id}/{integration_type}/test", response_model=TestConnectionResponse)
async def test_integration_connection(
    project_id: int,
    integration_type: str,
    data: TestConnectionRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Test connection to an external service with provided config and return available projects."""
    try:
        integration = get_integration(integration_type, data.config)
        await integration.test_connection()
        
        # Fetch available projects on successful connection
        projects = []
        try:
            project_list = await integration.get_projects()
            projects = [
                RemoteProject(key=p.key, name=p.name, description=p.description)
                for p in project_list
            ]
        except Exception:
            # If fetching projects fails, still return success but without projects
            pass
        
        return TestConnectionResponse(
            success=True,
            message="Connection successful",
            projects=projects if projects else None
        )
    except IntegrationAuthError as e:
        return TestConnectionResponse(success=False, message=str(e))
    except IntegrationConnectionError as e:
        return TestConnectionResponse(success=False, message=str(e))
    except IntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception:
        return TestConnectionResponse(
            success=False,
            message="Could not verify the connection. Check the URL and credentials, then try again.",
        )


@router.get("/{project_id}/{integration_type}/projects", response_model=ProjectListResponse)
async def list_remote_projects(
    project_id: int,
    integration_type: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List available projects from the remote service."""
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {integration_type}"
        )
    
    # Get saved config
    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == int_type
        )
    )
    db_integration = result.scalar_one_or_none()
    
    if not db_integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_type} not configured for this project"
        )
    
    try:
        # Decrypt config before using
        decrypted_config = decrypt_config(db_integration.config)
        integration = get_integration(integration_type, decrypted_config)
        projects = await integration.get_projects()
        return ProjectListResponse(projects=[p.model_dump() for p in projects])
    except IntegrationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
