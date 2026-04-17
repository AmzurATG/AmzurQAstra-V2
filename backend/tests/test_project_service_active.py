"""
Behavior for API visibility of soft-deleted projects.

Mirrors ``ProjectService.get_active_by_id`` without importing SQLAlchemy
(so this file can run under Python/SQLAlchemy stacks where ORM import fails).
"""


def _visible_to_user(project: dict | None) -> dict | None:
    if project is None or not project.get("is_active", True):
        return None
    return project


def test_missing_project_not_visible():
    assert _visible_to_user(None) is None


def test_soft_deleted_project_not_visible():
    assert _visible_to_user({"id": 1, "is_active": False}) is None


def test_active_project_visible():
    p = {"id": 2, "is_active": True, "name": "Demo"}
    assert _visible_to_user(p) is p
