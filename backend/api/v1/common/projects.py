"""
Project Management Endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from common.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from common.services.project_service import ProjectService
from common.db.models.project import Project


router = APIRouter()

_DUPLICATE_PROJECT_NAME = "duplicate_project_name"
_DUPLICATE_MSG = "A project with this name already exists for your account."


def project_to_response(project: Project) -> dict:
    """Convert project model to response dict with credentials info."""
    creds = project.app_credentials or {}
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "app_url": project.app_url,
        "is_active": project.is_active,
        "owner_id": project.owner_id,
        "organization_id": project.organization_id,
        "jira_project_key": project.jira_project_key,
        "azure_devops_project": project.azure_devops_project,
        "has_credentials": bool(creds.get("username") or creds.get("password")),
        "app_username": creds.get("username"),
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    search: str = Query(None, description="Search by project name"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects accessible to the current user."""
    project_service = ProjectService(db)
    projects, total = await project_service.get_list(
        owner_id=current_user.id if not current_user.is_superuser else None,
        search=search,
        pagination=pagination,
    )
    
    return PaginatedResponse.create(
        items=[project_to_response(p) for p in projects],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project_service = ProjectService(db)
    try:
        project = await project_service.create(project_data, owner_id=current_user.id)
    except ValueError as exc:
        if str(exc) == _DUPLICATE_PROJECT_NAME:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_DUPLICATE_MSG,
            ) from None
        raise
    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a project by ID."""
    project_service = ProjectService(db)
    project = await project_service.get_active_by_id(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check access
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project",
        )
    
    return project_to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    project_service = ProjectService(db)
    project = await project_service.get_active_by_id(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check ownership
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this project",
        )
    
    try:
        updated_project = await project_service.update(project_id, project_data)
    except ValueError as exc:
        if str(exc) == _DUPLICATE_PROJECT_NAME:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_DUPLICATE_MSG,
            ) from None
        raise
    return project_to_response(updated_project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project (soft delete)."""
    project_service = ProjectService(db)
    project = await project_service.get_by_id(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    # Check ownership
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project",
        )

    if not project.is_active:
        return None
    
    await project_service.delete(project_id)
