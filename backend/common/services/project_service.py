"""
Project Service
"""
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from common.db.models.project import Project
from common.schemas.project import ProjectCreate, ProjectUpdate
from common.api.pagination import PaginationParams


class ProjectService:
    """Service for project operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, project_id: int) -> Optional[Project]:
        """Get project by ID."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        owner_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        search: Optional[str] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Tuple[List[Project], int]:
        """Get list of projects with filters."""
        query = select(Project).where(Project.is_active == True)
        count_query = select(func.count(Project.id)).where(Project.is_active == True)
        
        if owner_id:
            query = query.where(Project.owner_id == owner_id)
            count_query = count_query.where(Project.owner_id == owner_id)
        
        if organization_id:
            query = query.where(Project.organization_id == organization_id)
            count_query = count_query.where(Project.organization_id == organization_id)
        
        if search:
            search_filter = f"%{search}%"
            query = query.where(Project.name.ilike(search_filter))
            count_query = count_query.where(Project.name.ilike(search_filter))
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.page_size)
        
        query = query.order_by(Project.created_at.desc())
        
        result = await self.db.execute(query)
        projects = result.scalars().all()
        
        return list(projects), total
    
    async def create(self, project_data: ProjectCreate, owner_id: int) -> Project:
        """Create a new project."""
        data = project_data.model_dump(exclude={'app_username', 'app_password'})
        
        # Store credentials in app_credentials JSONB if provided
        if project_data.app_username or project_data.app_password:
            data['app_credentials'] = {
                'username': project_data.app_username,
                'password': project_data.app_password,
            }
        
        project = Project(
            **data,
            owner_id=owner_id,
        )
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return project
    
    async def update(
        self, project_id: int, project_data: ProjectUpdate
    ) -> Optional[Project]:
        """Update a project."""
        project = await self.get_by_id(project_id)
        if not project:
            return None
        
        update_data = project_data.model_dump(exclude_unset=True)
        
        # Handle credentials merge - keep existing values if not provided
        if 'app_credentials' in update_data and update_data['app_credentials']:
            existing_creds = project.app_credentials or {}
            new_creds = update_data['app_credentials']
            
            # Merge: only update fields that are provided and non-empty
            merged_creds = existing_creds.copy()
            if new_creds.get('username'):
                merged_creds['username'] = new_creds['username']
            if new_creds.get('password'):
                merged_creds['password'] = new_creds['password']
            
            update_data['app_credentials'] = merged_creds if merged_creds else None
        
        for field, value in update_data.items():
            setattr(project, field, value)
        
        await self.db.flush()
        await self.db.refresh(project)
        return project
    
    async def delete(self, project_id: int) -> bool:
        """Soft delete a project."""
        project = await self.get_by_id(project_id)
        if not project:
            return False
        
        project.is_active = False
        await self.db.flush()
        return True
