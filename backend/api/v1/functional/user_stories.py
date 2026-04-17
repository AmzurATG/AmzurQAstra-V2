"""
User Stories API — core CRUD, stats, and sprints.

Sync and generate-tests live in sibling modules to keep files maintainable.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.api.deps import get_current_active_user
from common.api.pagination import PaginatedResponse, PaginationParams
from common.db.database import get_db
from common.db.models.integration import IntegrationType, ProjectIntegration
from common.db.models.user import User
from common.db.models.user_story import (
    UserStory,
    UserStoryPriority,
    UserStorySource,
    UserStoryStatus,
)
from common.integrations import get_integration
from common.integrations.exceptions import IntegrationError
from common.utils.security import decrypt_config
from features.functional.db.models.test_case import TestCase

from api.v1.functional.user_story_generate import router as user_story_generate_router
from api.v1.functional.user_story_response_mapper import user_story_to_response
from api.v1.functional.user_story_schemas import (
    DeleteUserStoryResponse,
    SprintResponse,
    StoryStatsResponse,
    UserStoryCreate,
    UserStoryResponse,
    UserStoryUpdate,
)
from api.v1.functional.user_story_sync import router as user_story_sync_router
from features.functional.services.user_story_link_counts import (
    test_case_stats_by_user_story_ids,
    test_case_stats_for_user_story,
)

router = APIRouter()
router.include_router(user_story_sync_router)
router.include_router(user_story_generate_router)


def _parse_sprint_ids_csv(raw: Optional[str]) -> Optional[List[str]]:
    if not raw or not raw.strip():
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or None


@router.get("/{project_id}/stats", response_model=StoryStatsResponse)
async def get_user_story_stats(
    project_id: int,
    sprint_ids: Optional[str] = Query(
        None,
        description="Comma-separated external sprint ids; scopes stats to those sprints (Jira)",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sprint_parts = _parse_sprint_ids_csv(sprint_ids)
    base = [UserStory.project_id == project_id]
    if sprint_parts:
        base.append(UserStory.sprint_id.in_(sprint_parts))
    scope = and_(*base)

    result = await db.execute(
        select(
            func.count(UserStory.id).label("total"),
            func.count(UserStory.id)
            .filter(UserStory.status == UserStoryStatus.open)
            .label("open"),
            func.count(UserStory.id)
            .filter(UserStory.status == UserStoryStatus.in_progress)
            .label("in_progress"),
            func.count(UserStory.id)
            .filter(UserStory.status == UserStoryStatus.done)
            .label("done"),
            func.count(UserStory.id)
            .filter(UserStory.status == UserStoryStatus.blocked)
            .label("blocked"),
            func.count(UserStory.id)
            .filter(UserStory.status == UserStoryStatus.closed)
            .label("closed"),
        ).where(scope)
    )
    row = result.one()
    return StoryStatsResponse(
        total=row.total,
        open=row.open,
        in_progress=row.in_progress,
        done=row.done,
        blocked=row.blocked,
        closed=row.closed,
    )


@router.get("/{project_id}/sprints", response_model=List[SprintResponse])
async def get_sprints(
    project_id: int,
    integration_type: str = "jira",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {integration_type}",
        )

    result = await db.execute(
        select(ProjectIntegration).where(
            ProjectIntegration.project_id == project_id,
            ProjectIntegration.integration_type == int_type,
        )
    )
    db_integration = result.scalar_one_or_none()

    if not db_integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integration {integration_type} not configured for this project",
        )

    if not db_integration.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration {integration_type} is disabled",
        )

    try:
        decrypted_config = decrypt_config(db_integration.config)
        integration = get_integration(integration_type, decrypted_config)

        if integration_type == "jira" and hasattr(integration, "get_sprints"):
            sprints = await integration.get_sprints()
            return [
                SprintResponse(
                    id=s.get("id"),
                    name=s.get("name", "Unknown"),
                    state=s.get("state", "unknown"),
                    start_date=s.get("startDate"),
                    end_date=s.get("endDate"),
                )
                for s in sprints
            ]

        return []
    except IntegrationError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get("/{project_id}", response_model=PaginatedResponse[UserStoryResponse])
async def list_user_stories(
    project_id: int,
    status: Optional[UserStoryStatus] = None,
    priority: Optional[UserStoryPriority] = None,
    source: Optional[UserStorySource] = None,
    search: Optional[str] = None,
    sprint_ids: Optional[str] = Query(
        None,
        description="Comma-separated external sprint ids; limits rows to those sprints (matches last sync scope)",
    ),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    sprint_parts = _parse_sprint_ids_csv(sprint_ids)

    query = select(UserStory).where(UserStory.project_id == project_id)
    count_query = select(func.count(UserStory.id)).where(
        UserStory.project_id == project_id
    )

    if sprint_parts:
        query = query.where(UserStory.sprint_id.in_(sprint_parts))
        count_query = count_query.where(UserStory.sprint_id.in_(sprint_parts))

    if status:
        query = query.where(UserStory.status == status)
        count_query = count_query.where(UserStory.status == status)

    if priority:
        query = query.where(UserStory.priority == priority)
        count_query = count_query.where(UserStory.priority == priority)

    if source:
        query = query.where(UserStory.source == source)
        count_query = count_query.where(UserStory.source == source)

    if search:
        search_filter = UserStory.title.ilike(f"%{search}%") | UserStory.external_key.ilike(
            f"%{search}%"
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(UserStory.updated_at.desc())
    query = query.offset((pagination.page - 1) * pagination.page_size).limit(
        pagination.page_size
    )

    result = await db.execute(query)
    stories = result.scalars().all()
    story_ids = [s.id for s in stories]
    total_map, gen_map = await test_case_stats_by_user_story_ids(db, story_ids)

    items = [
        user_story_to_response(
            s,
            linked_test_cases=total_map.get(s.id, 0),
            generated_test_cases=gen_map.get(s.id, 0),
            linked_requirements=0,
        )
        for s in stories
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/{project_id}", response_model=UserStoryResponse, status_code=status.HTTP_201_CREATED)
async def create_user_story(
    project_id: int,
    data: UserStoryCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    story = UserStory(
        project_id=project_id,
        title=data.title,
        description=data.description,
        acceptance_criteria=data.acceptance_criteria,
        status=data.status,
        priority=data.priority,
        item_type=data.item_type,
        parent_key=data.parent_key,
        story_points=data.story_points,
        assignee=data.assignee,
        labels=data.labels or [],
        source=UserStorySource.manual,
    )

    db.add(story)
    await db.commit()
    await db.refresh(story)

    return user_story_to_response(
        story,
        linked_test_cases=0,
        generated_test_cases=0,
        linked_requirements=0,
    )


@router.get("/{project_id}/{story_id}", response_model=UserStoryResponse)
async def get_user_story(
    project_id: int,
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id,
            UserStory.project_id == project_id,
        )
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found",
        )

    total, gen = await test_case_stats_for_user_story(db, story_id)
    return user_story_to_response(
        story,
        linked_test_cases=total,
        generated_test_cases=gen,
        linked_requirements=0,
    )


@router.put("/{project_id}/{story_id}", response_model=UserStoryResponse)
async def update_user_story(
    project_id: int,
    story_id: int,
    data: UserStoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id,
            UserStory.project_id == project_id,
        )
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)

    await db.commit()
    await db.refresh(story)

    total, gen = await test_case_stats_for_user_story(db, story_id)
    return user_story_to_response(
        story,
        linked_test_cases=total,
        generated_test_cases=gen,
        linked_requirements=0,
    )


@router.delete("/{project_id}/{story_id}", response_model=DeleteUserStoryResponse)
async def delete_user_story(
    project_id: int,
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id,
            UserStory.project_id == project_id,
        )
    )
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found",
        )

    test_cases_result = await db.execute(
        select(TestCase).where(TestCase.user_story_id == story_id)
    )
    test_cases = test_cases_result.scalars().all()
    test_cases_count = len(test_cases)

    for test_case in test_cases:
        await db.delete(test_case)

    await db.delete(story)
    await db.commit()

    return DeleteUserStoryResponse(
        message=f"User story and {test_cases_count} related test case(s) deleted successfully",
        test_cases_deleted=test_cases_count,
    )
