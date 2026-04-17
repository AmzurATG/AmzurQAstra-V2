"""Batch counts of test cases linked to user stories (for API responses)."""
from typing import Dict, List, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.db.models.test_case import TestCase


async def test_case_counts_by_user_story_ids(
    db: AsyncSession, story_ids: List[int]
) -> Dict[int, int]:
    """Return map of user_story_id -> total number of test cases."""
    total, _ = await test_case_stats_by_user_story_ids(db, story_ids)
    return total


async def test_case_stats_by_user_story_ids(
    db: AsyncSession, story_ids: List[int]
) -> Tuple[Dict[int, int], Dict[int, int]]:
    """Return (total_by_story, generated_by_story)."""
    if not story_ids:
        return {}, {}
    gen_sum = func.sum(case((TestCase.is_generated.is_(True), 1), else_=0))
    result = await db.execute(
        select(
            TestCase.user_story_id,
            func.count(TestCase.id).label("total"),
            gen_sum.label("generated"),
        )
        .where(TestCase.user_story_id.in_(story_ids))
        .group_by(TestCase.user_story_id)
    )
    total_map: Dict[int, int] = {}
    gen_map: Dict[int, int] = {}
    for row in result.all():
        sid = row[0]
        if sid is None:
            continue
        total_map[sid] = int(row[1] or 0)
        gen_map[sid] = int(row[2] or 0)
    return total_map, gen_map


async def test_case_stats_for_user_story(
    db: AsyncSession, story_id: int
) -> Tuple[int, int]:
    """Return (total test cases, generated test cases) for one story."""
    t, g = await test_case_stats_by_user_story_ids(db, [story_id])
    return t.get(story_id, 0), g.get(story_id, 0)
