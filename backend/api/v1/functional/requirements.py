"""
Requirements Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from features.functional.schemas.requirement import (
    RequirementCreate,
    RequirementUpdate,
    RequirementResponse,
)
from features.functional.services.requirement_service import RequirementService


router = APIRouter()


@router.get("/", response_model=PaginatedResponse[RequirementResponse])
async def list_requirements(
    project_id: int,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List requirements for a project."""
    service = RequirementService(db)
    requirements, total = await service.get_list(project_id, pagination)
    
    return PaginatedResponse.create(
        items=requirements,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/", response_model=RequirementResponse, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    requirement_data: RequirementCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new requirement."""
    service = RequirementService(db)
    requirement = await service.create(requirement_data)
    return requirement


@router.post("/upload", response_model=RequirementResponse)
async def upload_requirement_document(
    project_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a requirement document (PDF, Word, Markdown)."""
    service = RequirementService(db)
    requirement = await service.create_from_upload(
        project_id=project_id,
        title=title,
        file=file,
    )
    return requirement


@router.get("/{requirement_id}", response_model=RequirementResponse)
async def get_requirement(
    requirement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a requirement by ID."""
    service = RequirementService(db)
    requirement = await service.get_by_id(requirement_id)
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found",
        )
    
    return requirement


@router.put("/{requirement_id}", response_model=RequirementResponse)
async def update_requirement(
    requirement_id: int,
    requirement_data: RequirementUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a requirement."""
    service = RequirementService(db)
    requirement = await service.update(requirement_id, requirement_data)
    
    if not requirement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found",
        )
    
    return requirement


@router.delete("/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    requirement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a requirement."""
    service = RequirementService(db)
    deleted = await service.delete(requirement_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requirement not found",
        )


@router.post("/{requirement_id}/generate-test-cases", response_model=dict)
async def generate_test_cases_from_requirement(
    requirement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate test cases from a requirement using LLM."""
    from features.functional.services.test_case_generation_service import TestCaseGenerationService
    service = TestCaseGenerationService(db)
    result = await service.generate_test_cases_from_requirement(requirement_id)
    return result
