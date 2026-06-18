"""
Validation helpers for manual test step create/update.
"""
from typing import List, Optional

from features.functional.db.models.test_step import TestStepAction

_ACTIONS_REQUIRING_TARGET = {
    TestStepAction.navigate,
    TestStepAction.click,
    TestStepAction.fill,
    TestStepAction.type,
    TestStepAction.select,
    TestStepAction.check,
    TestStepAction.uncheck,
    TestStepAction.hover,
    TestStepAction.assert_visible,
    TestStepAction.assert_text,
    TestStepAction.assert_title,
}

_ACTIONS_REQUIRING_VALUE = {
    TestStepAction.fill,
    TestStepAction.type,
    TestStepAction.select,
    TestStepAction.assert_url,
    TestStepAction.assert_text,
}


def validate_step_fields(
    *,
    action: TestStepAction,
    description: Optional[str],
    target: Optional[str],
    value: Optional[str],
) -> List[str]:
    """Return human-readable validation errors (empty if valid)."""
    errors: List[str] = []
    desc = (description or "").strip()
    tgt = (target or "").strip()
    val = (value or "").strip()

    if not desc:
        errors.append("Description is required")

    if action in _ACTIONS_REQUIRING_TARGET and not tgt:
        errors.append(f"Target is required for action '{action.value}'")

    if action in _ACTIONS_REQUIRING_VALUE and not val:
        errors.append(f"Value is required for action '{action.value}'")

    return errors


def normalize_insert_step_number(
    requested: Optional[int], existing_count: int
) -> int:
    """
    Resolve insert position to 1..existing_count+1.
    None or too large => append at end.
    """
    if existing_count == 0:
        return 1
    if requested is None:
        return existing_count + 1
    if requested < 1:
        return 1
    if requested > existing_count + 1:
        return existing_count + 1
    return requested
