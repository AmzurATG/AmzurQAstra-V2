"""Map UserStory ORM rows to API response models (DRY)."""
from common.db.models.user_story import UserStory
from api.v1.functional.user_story_schemas import UserStoryResponse


def user_story_to_response(
    story: UserStory,
    *,
    linked_test_cases: int = 0,
    generated_test_cases: int = 0,
    linked_requirements: int = 0,
) -> UserStoryResponse:
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
        labels=list(story.labels) if story.labels else [],
        sprint_id=story.sprint_id,
        sprint_name=story.sprint_name,
        integrity_check=story.integrity_check,
        linked_test_cases=linked_test_cases,
        generated_test_cases=generated_test_cases,
        linked_requirements=linked_requirements,
        last_synced_at=story.last_synced_at,
        external_updated_at=story.external_updated_at,
        external_created_at=story.external_created_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )
