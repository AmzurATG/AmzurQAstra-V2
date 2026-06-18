"""
Pure helpers for test step ordering (used by service + unit tests).
"""
from typing import Iterable, List


def step_numbers_after_insert_shift(
    existing_step_numbers: Iterable[int], insert_at: int
) -> List[int]:
    """Return new step_number for each existing step after inserting at insert_at."""
    return [
        n + 1 if n >= insert_at else n
        for n in sorted(existing_step_numbers)
    ]


def step_numbers_after_delete_shift(
    existing_step_numbers: Iterable[int], deleted_at: int
) -> List[int]:
    """Return new step_number for remaining steps after deleting deleted_at."""
    return [
        n - 1 if n > deleted_at else n
        for n in sorted(existing_step_numbers)
        if n != deleted_at
    ]
