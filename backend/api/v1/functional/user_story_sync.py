"""Sync user stories from external PM tools."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
from common.integrations import get_integration
from common.integrations.base import ProjectManagementIntegration
from common.integrations.exceptions import IntegrationError
from common.utils.security import decrypt_config
from api.v1.functional.user_story_schemas import SyncRequest, SyncResponse

router = APIRouter()


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
            detail=f"Invalid integration type: {data.integration_type}",
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
            detail=f"Integration {data.integration_type} not configured for this project",
        )

    if not db_integration.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration {data.integration_type} is disabled",
        )

    db_integration.sync_status = SyncStatus.syncing
    await db.commit()

    try:
        decrypted_config = decrypt_config(db_integration.config)
        integration = get_integration(data.integration_type, decrypted_config)

        if not isinstance(integration, ProjectManagementIntegration):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{data.integration_type} is not a project management integration",
            )

        project_key = data.project_key
        if not project_key:
            project_key = (
                decrypted_config.get("project_key")
                or decrypted_config.get("project_id")
                or decrypted_config.get("project")
            )

        if not project_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No project key specified in integration config or request",
            )

        if data.force_full_sync:
            effective_updated_since = None
        elif data.updated_since is not None:
            effective_updated_since = data.updated_since
        elif db_integration.last_sync_at is not None:
            effective_updated_since = db_integration.last_sync_at
        else:
            effective_updated_since = None

        fetch_kwargs = dict(
            project_key=project_key,
            issue_types=data.issue_types,
            updated_since=effective_updated_since,
        )
        # Only Jira's client accepts sprint filter kwargs.
        if int_type == IntegrationType.jira:
            sprint_ids: Optional[List[int]] = None
            if data.sprint_ids:
                sprint_ids = list(dict.fromkeys(data.sprint_ids))
            elif data.sprint_id is not None:
                sprint_ids = [data.sprint_id]
            if sprint_ids:
                fetch_kwargs["sprint_ids"] = sprint_ids

        external_stories = await integration.fetch_user_stories(**fetch_kwargs)

        source_map = {
            "jira": UserStorySource.jira,
            "redmine": UserStorySource.redmine,
            "azure_devops": UserStorySource.azure_devops,
        }
        source = source_map.get(data.integration_type, UserStorySource.manual)

        priority_map = {
            "low": UserStoryPriority.low,
            "medium": UserStoryPriority.medium,
            "high": UserStoryPriority.high,
            "critical": UserStoryPriority.critical,
        }

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
                existing_result = await db.execute(
                    select(UserStory).where(
                        UserStory.project_id == project_id,
                        UserStory.external_id == ext_story.external_id,
                        UserStory.source == source,
                    )
                )
                existing = existing_result.scalar_one_or_none()

                priority = UserStoryPriority.medium
                if ext_story.priority:
                    priority = priority_map.get(ext_story.priority.lower(), UserStoryPriority.medium)

                story_status = UserStoryStatus.open
                if ext_story.status:
                    story_status = status_map.get(ext_story.status.lower(), UserStoryStatus.open)

                item_type_enum = UserStoryItemType.story
                if ext_story.item_type:
                    item_type_enum = item_type_map.get(
                        ext_story.item_type.lower(), UserStoryItemType.story
                    )

                if existing:
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
        db_integration.last_sync_error = str(e)[:2000]
        await db.commit()

        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        db_integration.sync_status = SyncStatus.failed
        db_integration.last_sync_error = str(e)[:2000]
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}",
        )
