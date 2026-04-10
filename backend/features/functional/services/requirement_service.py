"""
Requirement Service
"""
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, UploadFile, status

from common.api.pagination import PaginationParams
from config import settings
from features.functional.db.models.requirement import Requirement, RequirementSourceType
from features.functional.schemas.requirement import RequirementCreate, RequirementUpdate
from features.functional.core.document_parser import get_document_parser
from features.functional.core.storage import get_storage_adapter, StorageAdapter


class RequirementService:
    """Service for requirement operations."""
    
    def __init__(self, db: AsyncSession, storage: Optional[StorageAdapter] = None):
        self.db = db
        # Use provided storage adapter or get default from config
        self._storage = storage or get_storage_adapter()
    
    async def get_by_id(self, requirement_id: int) -> Optional[Requirement]:
        """Get requirement by ID."""
        result = await self.db.execute(
            select(Requirement)
            .options(selectinload(Requirement.test_cases))
            .where(Requirement.id == requirement_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        project_id: int,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get list of requirements for a project with test case counts."""
        # Query with test cases relationship
        query = (
            select(Requirement)
            .options(selectinload(Requirement.test_cases))
            .where(Requirement.project_id == project_id)
        )
        count_query = select(func.count(Requirement.id)).where(
            Requirement.project_id == project_id
        )
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        
        query = query.order_by(Requirement.created_at.desc())
        
        result = await self.db.execute(query)
        requirements = result.scalars().all()
        
        # Convert to dict with test_cases_count
        items = []
        for req in requirements:
            item = {
                "id": req.id,
                "project_id": req.project_id,
                "title": req.title,
                "content": req.content,
                "source_type": req.source_type,
                "source": req.source_type.value if req.source_type else "manual",
                "source_url": req.source_url,
                "source_id": req.source_id,
                "file_path": req.file_path,
                "file_name": req.file_name,
                "file_type": req.file_type,
                "created_at": req.created_at,
                "updated_at": req.updated_at,
                "test_cases_count": len(req.test_cases) if req.test_cases else 0,
                "status": "processed",
            }
            items.append(item)
        
        return items, total
    
    async def create(self, requirement_data: RequirementCreate) -> Requirement:
        """Create a new requirement."""
        requirement = Requirement(**requirement_data.model_dump())
        self.db.add(requirement)
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement
    
    async def create_from_upload(
        self,
        project_id: int,
        title: str,
        file: UploadFile,
    ) -> Requirement:
        """Create a requirement from an uploaded document."""
        # Read file content
        file_content = await file.read()
        max_b = settings.REQUIREMENT_UPLOAD_MAX_BYTES
        n = len(file_content)
        if n > max_b:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File size is {n:,} bytes; maximum allowed is {max_b:,} bytes (5 MiB)."
                ),
            )
        await file.seek(0)  # Reset for parsing

        # storage/Requirements/{project_id}/ under STORAGE_LOCAL_PATH (../storage)
        storage_file = await self._storage.save(
            file_content=file_content,
            filename=file.filename or "document",
            content_type=file.content_type or "application/octet-stream",
            subdirectory=f"Requirements/{project_id}",
        )
        
        # Parse document
        parser = get_document_parser(file.filename)
        content = await parser.parse(file)
        
        # Create requirement
        requirement = Requirement(
            project_id=project_id,
            title=title,
            content=content,
            source_type=RequirementSourceType.UPLOAD,
            file_path=storage_file.path,
            file_name=storage_file.filename,
            file_type=storage_file.content_type,
        )
        
        self.db.add(requirement)
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement

    async def get_file_bytes(self, requirement_id: int) -> Tuple[bytes, str, str]:
        """Return raw file bytes, original filename, and Content-Type for HTTP serving."""
        requirement = await self.get_by_id(requirement_id)
        if not requirement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found",
            )
        if not requirement.file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file is attached to this requirement",
            )
        path_key = requirement.file_path.replace("\\", "/")
        raw = await self._storage.get(path_key)
        if raw is None:
            raw = await self._storage.get(requirement.file_path)
        if raw is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage",
            )
        filename = requirement.file_name or "document"
        media = requirement.file_type or "application/octet-stream"
        return raw, filename, media

    async def update(
        self, requirement_id: int, requirement_data: RequirementUpdate
    ) -> Optional[Requirement]:
        """Update a requirement."""
        requirement = await self.get_by_id(requirement_id)
        if not requirement:
            return None
        
        update_data = requirement_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(requirement, field, value)
        
        await self.db.flush()
        await self.db.refresh(requirement)
        return requirement
    
    async def delete(self, requirement_id: int) -> bool:
        """Delete a requirement."""
        requirement = await self.get_by_id(requirement_id)
        if not requirement:
            return False
        
        # Delete associated file if exists
        if requirement.file_path:
            await self._storage.delete(requirement.file_path)
        
        await self.db.delete(requirement)
        await self.db.flush()
        return True
