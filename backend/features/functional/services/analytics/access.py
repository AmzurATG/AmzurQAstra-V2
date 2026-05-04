"""Project access guard for analytics (owner or superuser, active project)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.project import Project
from common.db.models.user import User


async def assert_project_access(db: AsyncSession, user: User, project_id: int) -> Project:
    project = await db.get(Project, project_id)
    if project is None or not project.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not user.is_superuser and project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this project")
    return project
