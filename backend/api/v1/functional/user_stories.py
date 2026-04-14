"""
User Stories API Endpoints

Manages user stories imported from PM tools or created manually.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from common.db.database import get_db
from common.db.models.user import User
from common.db.models.user_story import (
    UserStory,
    UserStoryStatus,
    UserStoryPriority,
    UserStorySource,
    UserStoryItemType,
)
from common.db.models.integration import ProjectIntegration, IntegrationType, SyncStatus
from common.api.deps import get_current_active_user
from common.api.pagination import PaginationParams, PaginatedResponse
from common.integrations import get_integration
from common.integrations.base import ProjectManagementIntegration
from common.integrations.exceptions import IntegrationError
from common.utils.security import decrypt_config
from features.functional.db.models.test_case import TestCase


router = APIRouter()


# =====================================================
# SCHEMAS
# =====================================================

class UserStoryCreate(BaseModel):
    """Create user story manually"""
    project_id: int
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: UserStoryStatus = UserStoryStatus.open
    priority: UserStoryPriority = UserStoryPriority.medium
    item_type: UserStoryItemType = UserStoryItemType.story
    parent_key: Optional[str] = None
    story_points: Optional[int] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    integrity_check: bool = False


class UserStoryUpdate(BaseModel):
    """Update user story"""
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: Optional[UserStoryStatus] = None
    priority: Optional[UserStoryPriority] = None
    item_type: Optional[UserStoryItemType] = None
    parent_key: Optional[str] = None
    story_points: Optional[int] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    integrity_check: Optional[bool] = None


class UserStoryResponse(BaseModel):
    """User story response"""
    id: int
    project_id: int
    external_id: Optional[str]
    external_key: Optional[str]
    external_url: Optional[str]
    source: str
    integration_id: Optional[int]
    title: str
    description: Optional[str]
    acceptance_criteria: Optional[str]
    status: str
    priority: str
    item_type: str
    parent_key: Optional[str]
    story_points: Optional[int]
    assignee: Optional[str]
    reporter: Optional[str]
    labels: Optional[List[str]]
    sprint_id: Optional[str] = None
    sprint_name: Optional[str] = None
    integrity_check: bool = False
    last_synced_at: Optional[datetime]
    external_updated_at: Optional[datetime]
    external_created_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    """Sync request parameters"""
    integration_type: str
    project_key: Optional[str] = None  # Override project key from config
    sprint_id: Optional[int] = None  # Filter by sprint (None = all sprints)
    issue_types: Optional[List[str]] = None
    updated_since: Optional[datetime] = None
    # When True: ignore last_sync_at / cursor and fetch all matching remote issues
    force_full_sync: bool = False


class SyncResponse(BaseModel):
    """Sync response"""
    status: str
    message: str
    items_synced: int
    errors: List[str] = []


class StoryStatsResponse(BaseModel):
    """User story statistics"""
    total: int
    open: int
    in_progress: int
    done: int
    blocked: int


# =====================================================
# ENDPOINTS
# =====================================================

@router.get("/{project_id}/stats", response_model=StoryStatsResponse)
async def get_user_story_stats(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user story statistics for a project."""
    result = await db.execute(
        select(
            func.count(UserStory.id).label('total'),
            func.count(UserStory.id).filter(UserStory.status == UserStoryStatus.open).label('open'),
            func.count(UserStory.id).filter(UserStory.status == UserStoryStatus.in_progress).label('in_progress'),
            func.count(UserStory.id).filter(UserStory.status == UserStoryStatus.done).label('done'),
            func.count(UserStory.id).filter(UserStory.status == UserStoryStatus.blocked).label('blocked'),
        ).where(UserStory.project_id == project_id)
    )
    row = result.one()
    
    return StoryStatsResponse(
        total=row.total,
        open=row.open,
        in_progress=row.in_progress,
        done=row.done,
        blocked=row.blocked,
    )


class SprintResponse(BaseModel):
    """Sprint response from Jira"""
    id: int
    name: str
    state: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/{project_id}/sprints", response_model=List[SprintResponse])
async def get_sprints(
    project_id: int,
    integration_type: str = "jira",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get available sprints from the PM tool integration."""
    try:
        int_type = IntegrationType(integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {integration_type}"
        )
    
    # Get integration config
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
    
    if not db_integration.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration {integration_type} is disabled"
        )
    
    try:
        decrypted_config = decrypt_config(db_integration.config)
        integration = get_integration(integration_type, decrypted_config)
        
        # Only Jira supports sprints for now
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
            detail=str(e)
        )


@router.get("/{project_id}", response_model=PaginatedResponse[UserStoryResponse])
async def list_user_stories(
    project_id: int,
    status: Optional[UserStoryStatus] = None,
    priority: Optional[UserStoryPriority] = None,
    source: Optional[UserStorySource] = None,
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List user stories for a project with filtering."""
    query = select(UserStory).where(UserStory.project_id == project_id)
    count_query = select(func.count(UserStory.id)).where(UserStory.project_id == project_id)
    
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
        search_filter = UserStory.title.ilike(f"%{search}%") | UserStory.external_key.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(UserStory.updated_at.desc())
    query = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size)
    
    result = await db.execute(query)
    stories = result.scalars().all()
    
    items = [
        UserStoryResponse(
            id=s.id,
            project_id=s.project_id,
            external_id=s.external_id,
            external_key=s.external_key,
            external_url=s.external_url,
            source=s.source.value,
            integration_id=s.integration_id,
            title=s.title,
            description=s.description,
            acceptance_criteria=s.acceptance_criteria,
            status=s.status.value,
            priority=s.priority.value,
            item_type=s.item_type.value,
            parent_key=s.parent_key,
            story_points=s.story_points,
            assignee=s.assignee,
            reporter=s.reporter,
            labels=s.labels,
            integrity_check=s.integrity_check,
            last_synced_at=s.last_synced_at,
            external_updated_at=s.external_updated_at,
            external_created_at=s.external_created_at,
            created_at=s.created_at,
            updated_at=s.updated_at,
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
    """Create a new user story manually."""
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
    
    return UserStoryResponse(
        id=story.id,
        project_id=story.project_id,
        external_id=story.external_id,
        external_key=story.external_key,
        external_url=story.external_url,
        source=story.source.value,
        integration_id=story.integration_id,
        title=story.title,
        description=story.description,
        acceptance_criteria=story.acceptance_criteria,
        status=story.status.value,
        priority=story.priority.value,
        item_type=story.item_type.value,
        parent_key=story.parent_key,
        story_points=story.story_points,
        assignee=story.assignee,
        reporter=story.reporter,
        labels=story.labels,
        integrity_check=story.integrity_check,
        last_synced_at=story.last_synced_at,
        external_updated_at=story.external_updated_at,
        external_created_at=story.external_created_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


@router.get("/{project_id}/{story_id}", response_model=UserStoryResponse)
async def get_user_story(
    project_id: int,
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a user story by ID."""
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id,
            UserStory.project_id == project_id
        )
    )
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found"
        )
    
    return UserStoryResponse(
        id=story.id,
        project_id=story.project_id,
        external_id=story.external_id,
        external_key=story.external_key,
        external_url=story.external_url,
        source=story.source.value,
        integration_id=story.integration_id,
        title=story.title,
        description=story.description,
        acceptance_criteria=story.acceptance_criteria,
        status=story.status.value,
        priority=story.priority.value,
        item_type=story.item_type.value,
        parent_key=story.parent_key,
        story_points=story.story_points,
        assignee=story.assignee,
        reporter=story.reporter,
        labels=story.labels,
        integrity_check=story.integrity_check,
        last_synced_at=story.last_synced_at,
        external_updated_at=story.external_updated_at,
        external_created_at=story.external_created_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


@router.put("/{project_id}/{story_id}", response_model=UserStoryResponse)
async def update_user_story(
    project_id: int,
    story_id: int,
    data: UserStoryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user story."""
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id,
            UserStory.project_id == project_id
        )
    )
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found"
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(story, field, value)
    
    await db.commit()
    await db.refresh(story)
    
    return UserStoryResponse(
        id=story.id,
        project_id=story.project_id,
        external_id=story.external_id,
        external_key=story.external_key,
        external_url=story.external_url,
        source=story.source.value,
        integration_id=story.integration_id,
        title=story.title,
        description=story.description,
        acceptance_criteria=story.acceptance_criteria,
        status=story.status.value,
        priority=story.priority.value,
        item_type=story.item_type.value,
        parent_key=story.parent_key,
        story_points=story.story_points,
        assignee=story.assignee,
        reporter=story.reporter,
        labels=story.labels,
        integrity_check=story.integrity_check,
        last_synced_at=story.last_synced_at,
        external_updated_at=story.external_updated_at,
        external_created_at=story.external_created_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


class DeleteUserStoryResponse(BaseModel):
    """Response for delete user story"""
    message: str
    test_cases_deleted: int


@router.delete("/{project_id}/{story_id}", response_model=DeleteUserStoryResponse)
async def delete_user_story(
    project_id: int,
    story_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user story and all related test cases and test steps."""
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == story_id,
            UserStory.project_id == project_id
        )
    )
    story = result.scalar_one_or_none()
    
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found"
        )
    
    # Find and delete all related test cases (test steps will cascade delete)
    test_cases_result = await db.execute(
        select(TestCase).where(TestCase.user_story_id == story_id)
    )
    test_cases = test_cases_result.scalars().all()
    test_cases_count = len(test_cases)
    
    for test_case in test_cases:
        await db.delete(test_case)
    
    # Delete the user story
    await db.delete(story)
    await db.commit()
    
    return DeleteUserStoryResponse(
        message=f"User story and {test_cases_count} related test case(s) deleted successfully",
        test_cases_deleted=test_cases_count
    )


@router.post("/{project_id}/sync", response_model=SyncResponse)
async def sync_user_stories(
    project_id: int,
    data: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync user stories from an external PM tool."""
    try:
        int_type = IntegrationType(data.integration_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid integration type: {data.integration_type}"
        )
    
    # Get integration config
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
            detail=f"Integration {data.integration_type} not configured for this project"
        )
    
    if not db_integration.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration {data.integration_type} is disabled"
        )
    
    # Update sync status
    db_integration.sync_status = SyncStatus.syncing
    await db.commit()
    
    try:
        # Decrypt config before using
        decrypted_config = decrypt_config(db_integration.config)
        integration = get_integration(data.integration_type, decrypted_config)
        
        if not isinstance(integration, ProjectManagementIntegration):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{data.integration_type} is not a project management integration"
            )
        
        # Get project key from config or request
        project_key = data.project_key
        if not project_key:
            project_key = decrypted_config.get("project_key") or decrypted_config.get("project_id") or decrypted_config.get("project")
        
        if not project_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No project key specified in integration config or request"
            )

        # Effective incremental cursor unless force_full_sync
        if data.force_full_sync:
            effective_updated_since = None
        elif data.updated_since is not None:
            effective_updated_since = data.updated_since
        elif db_integration.last_sync_at is not None:
            effective_updated_since = db_integration.last_sync_at
        else:
            effective_updated_since = None

        # Fetch stories from external system
        external_stories = await integration.fetch_user_stories(
            project_key=project_key,
            issue_types=data.issue_types,
            updated_since=effective_updated_since,
            sprint_id=data.sprint_id,
        )
        
        # Map source type
        source_map = {
            "jira": UserStorySource.jira,
            "redmine": UserStorySource.redmine,
            "azure_devops": UserStorySource.azure_devops,
        }
        source = source_map.get(data.integration_type, UserStorySource.manual)
        
        # Map priority
        priority_map = {
            "low": UserStoryPriority.low,
            "medium": UserStoryPriority.medium,
            "high": UserStoryPriority.high,
            "critical": UserStoryPriority.critical,
        }
        
        # Map status
        status_map = {
            "open": UserStoryStatus.open,
            "new": UserStoryStatus.open,
            "to do": UserStoryStatus.open,
            "in progress": UserStoryStatus.in_progress,
            "in development": UserStoryStatus.in_progress,
            "active": UserStoryStatus.in_progress,
            "done": UserStoryStatus.done,
            "closed": UserStoryStatus.closed,
            "resolved": UserStoryStatus.done,
            "blocked": UserStoryStatus.blocked,
        }
        
        # Map item type
        item_type_map = {
            "epic": UserStoryItemType.epic,
            "story": UserStoryItemType.story,
            "bug": UserStoryItemType.bug,
            "task": UserStoryItemType.task,
            "subtask": UserStoryItemType.subtask,
            "feature": UserStoryItemType.feature,
            "requirement": UserStoryItemType.requirement,
        }
        
        synced_count = 0
        errors = []
        
        for ext_story in external_stories:
            try:
                # Check if story already exists
                existing_result = await db.execute(
                    select(UserStory).where(
                        UserStory.project_id == project_id,
                        UserStory.external_id == ext_story.external_id,
                        UserStory.source == source
                    )
                )
                existing = existing_result.scalar_one_or_none()
                
                # Map priority
                priority = UserStoryPriority.medium
                if ext_story.priority:
                    priority = priority_map.get(ext_story.priority.lower(), UserStoryPriority.medium)
                
                # Map status
                story_status = UserStoryStatus.open
                if ext_story.status:
                    story_status = status_map.get(ext_story.status.lower(), UserStoryStatus.open)
                
                # Map item type
                item_type_enum = UserStoryItemType.story
                if ext_story.item_type:
                    item_type_enum = item_type_map.get(ext_story.item_type.lower(), UserStoryItemType.story)
                
                if existing:
                    # Update existing story
                    existing.title = ext_story.title
                    existing.description = ext_story.description
                    existing.external_key = ext_story.external_key
                    existing.external_url = ext_story.external_url
                    existing.status = story_status
                    existing.priority = priority
                    existing.item_type = item_type_enum
                    existing.parent_key = ext_story.parent_key
                    existing.story_points = ext_story.story_points
                    existing.assignee = ext_story.assignee
                    existing.reporter = ext_story.reporter
                    existing.labels = ext_story.labels
                    existing.sprint_id = ext_story.sprint_id
                    existing.sprint_name = ext_story.sprint_name
                    existing.external_updated_at = ext_story.updated_at
                    existing.last_synced_at = datetime.utcnow()
                else:
                    # Create new story
                    story = UserStory(
                        project_id=project_id,
                        external_id=ext_story.external_id,
                        external_key=ext_story.external_key,
                        external_url=ext_story.external_url,
                        source=source,
                        integration_id=db_integration.id,
                        title=ext_story.title,
                        description=ext_story.description,
                        status=story_status,
                        priority=priority,
                        item_type=item_type_enum,
                        parent_key=ext_story.parent_key,
                        story_points=ext_story.story_points,
                        assignee=ext_story.assignee,
                        reporter=ext_story.reporter,
                        labels=ext_story.labels,
                        sprint_id=ext_story.sprint_id,
                        sprint_name=ext_story.sprint_name,
                        external_created_at=ext_story.created_at,
                        external_updated_at=ext_story.updated_at,
                        last_synced_at=datetime.utcnow(),
                    )
                    db.add(story)
                
                synced_count += 1
                
            except Exception as e:
                errors.append(f"Failed to sync {ext_story.external_key}: {str(e)}")
        
        # Update integration sync status
        db_integration.sync_status = SyncStatus.success
        db_integration.last_sync_at = datetime.utcnow()
        db_integration.last_sync_error = None
        db_integration.items_synced = synced_count
        
        await db.commit()
        
        return SyncResponse(
            status="success",
            message=f"Synced {synced_count} user stories from {data.integration_type}",
            items_synced=synced_count,
            errors=errors,
        )
        
    except IntegrationError as e:
        db_integration.sync_status = SyncStatus.failed
        db_integration.last_sync_error = str(e)[:2000]  # Truncate long errors
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )
    except Exception as e:
        db_integration.sync_status = SyncStatus.failed
        db_integration.last_sync_error = str(e)[:2000]  # Truncate long errors
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


# =====================================================
# TEST GENERATION ENDPOINTS
# =====================================================

class GenerateTestsRequest(BaseModel):
    """Request to generate test cases from a user story"""
    include_steps: bool = True


class GeneratedTestCaseInfo(BaseModel):
    """Info about a generated test case"""
    id: int
    title: str
    priority: str
    category: str


class GenerateTestsResponse(BaseModel):
    """Response from test generation"""
    success: bool
    user_story_id: int
    user_story_key: Optional[str] = None
    test_cases_created: int = 0
    test_cases: List[GeneratedTestCaseInfo] = []
    error: Optional[str] = None


@router.post(
    "/{project_id}/{user_story_id}/generate-tests",
    response_model=GenerateTestsResponse,
    summary="Generate test cases from a user story",
)
async def generate_tests_from_user_story(
    project_id: int,
    user_story_id: int,
    request: GenerateTestsRequest = GenerateTestsRequest(),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate test cases from a user story using AI/LLM.
    
    This endpoint uses the configured LLM (LiteLLM) to analyze the user story
    title, description, and acceptance criteria to generate appropriate test cases.
    
    Args:
        project_id: The project ID
        user_story_id: The user story ID to generate tests from
        request: Generation options (include_steps)
    
    Returns:
        GenerateTestsResponse with generated test case details
    """
    from features.functional.services.test_case_generation_service import TestCaseGenerationService
    
    # Verify user story exists and belongs to project
    result = await db.execute(
        select(UserStory).where(
            UserStory.id == user_story_id,
            UserStory.project_id == project_id
        )
    )
    user_story = result.scalar_one_or_none()
    
    if not user_story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User story not found"
        )
    
    # Generate test cases
    service = TestCaseGenerationService(db)
    result = await service.generate_test_cases_from_user_story(
        user_story_id=user_story_id,
        include_steps=request.include_steps,
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to generate test cases")
        )
    
    return GenerateTestsResponse(
        success=True,
        user_story_id=user_story_id,
        user_story_key=result.get("user_story_key"),
        test_cases_created=result.get("test_cases_created", 0),
        test_cases=[
            GeneratedTestCaseInfo(**tc)
            for tc in result.get("test_cases", [])
        ],
    )
