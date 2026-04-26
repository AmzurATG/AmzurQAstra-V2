"""Sync user stories from external PM tools."""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete, func
from sqlalchemy.orm.attributes import flag_modified

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
from features.functional.db.models.test_case import TestCase
from features.functional.db.models.test_step import TestStep
from features.functional.db.models.test_result import TestResult
from features.functional.db.models.test_run import TestRun
from common.integrations.exceptions import IntegrationError
from common.utils.security import decrypt_config, encrypt_config
from api.v1.functional.user_story_schemas import SyncRequest, SyncResponse

logger = logging.getLogger("qastra.integration.sync")

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

        logger.info(
            "Jira returned %d stories before post-filter (sprint_ids=%s)",
            len(external_stories),
            sprint_ids,
        )
        for s in external_stories:
            logger.info(
                "  [pre-filter] %s  sprint_id=%s  sprint_name=%s",
                s.external_key, s.sprint_id, s.sprint_name,
            )

        # Jira's JQL `sprint in (...)` matches by sprint *history*, so issues
        # that were once in a sprint but later removed can slip through.
        # Additionally, when "All sprints" is selected no JQL sprint clause is
        # added, which returns every issue in the project — including ones with
        # no current sprint.  Always drop stories without a current sprint, and
        # when specific sprints were requested keep only those.
        if int_type == IntegrationType.jira:
            if sprint_ids:
                requested = {str(sid) for sid in sprint_ids}
                external_stories = [
                    s for s in external_stories
                    if s.sprint_id and str(s.sprint_id) in requested
                ]
            else:
                # "All sprints" mode — still exclude stories with no sprint
                external_stories = [
                    s for s in external_stories
                    if s.sprint_id
                ]

        logger.info(
            "After post-filter: %d stories remain",
            len(external_stories),
        )
        for s in external_stories:
            logger.info(
                "  [post-filter] %s  sprint_id=%s  sprint_name=%s",
                s.external_key, s.sprint_id, s.sprint_name,
            )

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
                    # Only delete QA artefacts when the story actually
                    # changed in the external system (different updated_at).
                    # Stories from previously-selected sprints that haven't
                    # changed keep their test cases, steps, results & runs.
                    story_changed = (
                        existing.external_updated_at is None
                        or ext_story.updated_at is None
                        or existing.external_updated_at != ext_story.updated_at
                    )

                    if story_changed:
                        linked_tc_ids_result = await db.execute(
                            select(TestCase.id).where(
                                TestCase.user_story_id == existing.id
                            )
                        )
                        linked_tc_ids = [
                            row[0] for row in linked_tc_ids_result.fetchall()
                        ]
                        if linked_tc_ids:
                            # Collect test-run IDs that contain results for these cases
                            affected_run_ids_result = await db.execute(
                                select(TestResult.test_run_id.distinct()).where(
                                    TestResult.test_case_id.in_(linked_tc_ids)
                                )
                            )
                            affected_run_ids = [
                                row[0] for row in affected_run_ids_result.fetchall()
                            ]

                            # Remove test results that reference these test cases
                            await db.execute(
                                sa_delete(TestResult).where(
                                    TestResult.test_case_id.in_(linked_tc_ids)
                                )
                            )

                            # Delete test runs that are now empty
                            if affected_run_ids:
                                non_empty_run_ids_result = await db.execute(
                                    select(TestResult.test_run_id.distinct()).where(
                                        TestResult.test_run_id.in_(affected_run_ids)
                                    )
                                )
                                non_empty_run_ids = {
                                    row[0] for row in non_empty_run_ids_result.fetchall()
                                }
                                empty_run_ids = [
                                    rid for rid in affected_run_ids
                                    if rid not in non_empty_run_ids
                                ]
                                if empty_run_ids:
                                    await db.execute(
                                        sa_delete(TestRun).where(
                                            TestRun.id.in_(empty_run_ids)
                                        )
                                    )

                            # Remove test steps (bulk SQL won't trigger ORM cascade)
                            await db.execute(
                                sa_delete(TestStep).where(
                                    TestStep.test_case_id.in_(linked_tc_ids)
                                )
                            )

                            # Remove test cases
                            await db.execute(
                                sa_delete(TestCase).where(
                                    TestCase.id.in_(linked_tc_ids)
                                )
                            )

                    # Always refresh metadata fields
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

        # ── Remove stale stories no longer in the sync results ──
        # Collect the external_ids that came back in this sync batch.
        synced_external_ids = [s.external_id for s in external_stories if s.external_id]

        # Find stories from this integration that are NOT in the current results.
        stale_query = select(UserStory).where(
            UserStory.project_id == project_id,
            UserStory.integration_id == db_integration.id,
            UserStory.source == source,
        )
        if synced_external_ids:
            stale_query = stale_query.where(
                UserStory.external_id.notin_(synced_external_ids)
            )
        stale_result = await db.execute(stale_query)
        stale_stories = stale_result.scalars().all()

        removed_count = 0
        for stale_story in stale_stories:
            # Delete QA artefacts for each stale story
            stale_tc_ids_result = await db.execute(
                select(TestCase.id).where(
                    TestCase.user_story_id == stale_story.id
                )
            )
            stale_tc_ids = [row[0] for row in stale_tc_ids_result.fetchall()]

            if stale_tc_ids:
                # Collect affected test-run IDs
                affected_run_ids_result = await db.execute(
                    select(TestResult.test_run_id.distinct()).where(
                        TestResult.test_case_id.in_(stale_tc_ids)
                    )
                )
                affected_run_ids = [
                    row[0] for row in affected_run_ids_result.fetchall()
                ]

                # Remove test results
                await db.execute(
                    sa_delete(TestResult).where(
                        TestResult.test_case_id.in_(stale_tc_ids)
                    )
                )

                # Delete test runs that are now empty
                if affected_run_ids:
                    non_empty_result = await db.execute(
                        select(TestResult.test_run_id.distinct()).where(
                            TestResult.test_run_id.in_(affected_run_ids)
                        )
                    )
                    non_empty_ids = {
                        row[0] for row in non_empty_result.fetchall()
                    }
                    empty_run_ids = [
                        rid for rid in affected_run_ids
                        if rid not in non_empty_ids
                    ]
                    if empty_run_ids:
                        await db.execute(
                            sa_delete(TestRun).where(
                                TestRun.id.in_(empty_run_ids)
                            )
                        )

                # Remove test steps
                await db.execute(
                    sa_delete(TestStep).where(
                        TestStep.test_case_id.in_(stale_tc_ids)
                    )
                )

                # Remove test cases
                await db.execute(
                    sa_delete(TestCase).where(
                        TestCase.id.in_(stale_tc_ids)
                    )
                )

            # Delete the stale user story itself
            await db.delete(stale_story)
            removed_count += 1

        db_integration.sync_status = SyncStatus.success
        db_integration.last_sync_at = datetime.utcnow()
        db_integration.last_sync_error = None
        db_integration.items_synced = synced_count

        # Persist last sync scope on integration (non-sensitive) for cross-device Sync now + list filtering
        full_cfg = dict(decrypt_config(db_integration.config) or {})
        sync_scope: dict = {
            "integration_type": data.integration_type,
            "issue_types": list(data.issue_types or []),
            "force_full_sync": bool(data.force_full_sync),
        }
        if int_type == IntegrationType.jira:
            if data.sprint_ids:
                sync_scope["all_sprints"] = False
                sync_scope["sprint_ids"] = [int(x) for x in list(dict.fromkeys(data.sprint_ids))]
            elif data.sprint_id is not None:
                sync_scope["all_sprints"] = False
                sync_scope["sprint_ids"] = [int(data.sprint_id)]
            else:
                sync_scope["all_sprints"] = True
                sync_scope["sprint_ids"] = None
        else:
            sync_scope["all_sprints"] = True
            sync_scope["sprint_ids"] = None
        full_cfg["sync_scope"] = sync_scope
        db_integration.config = encrypt_config(full_cfg)
        flag_modified(db_integration, "config")

        await db.commit()

        return SyncResponse(
            status="success",
            message=(
                f"Synced {synced_count} user stories from {data.integration_type}"
                + (f", removed {removed_count} stale stories" if removed_count else "")
            ),
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
