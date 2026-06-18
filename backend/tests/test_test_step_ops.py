"""Unit tests for test step ordering helpers."""

from features.functional.services.test_step_ops import (
    step_numbers_after_delete_shift,
    step_numbers_after_insert_shift,
)
from features.functional.services.test_step_validation import (
    normalize_insert_step_number,
    validate_step_fields,
)
from features.functional.db.models.test_step import TestStepAction


def test_insert_shift_middle():
    assert step_numbers_after_insert_shift([1, 2, 3], 2) == [1, 3, 4]


def test_insert_shift_at_start():
    assert step_numbers_after_insert_shift([1, 2], 1) == [2, 3]


def test_insert_shift_append():
    assert step_numbers_after_insert_shift([1, 2], 3) == [1, 2]


def test_delete_shift_middle():
    assert step_numbers_after_delete_shift([1, 2, 3], 2) == [1, 2]


def test_delete_shift_first():
    assert step_numbers_after_delete_shift([1, 2, 3], 1) == [1, 2]


def test_normalize_insert_append():
    assert normalize_insert_step_number(None, 3) == 4
    assert normalize_insert_step_number(99, 3) == 4


def test_normalize_insert_middle():
    assert normalize_insert_step_number(2, 3) == 2


def test_validate_requires_description():
    errs = validate_step_fields(
        action=TestStepAction.click,
        description="",
        target="#btn",
        value=None,
    )
    assert any("Description" in e for e in errs)
