"""
Excel Story Mapper — resolves Excel story names to user_story_id integers.

Excel workbooks use human-readable story names (e.g. "User story -1.1 User
Registration & Age Verification") whereas QAstra stores AI-generated or
manually created story titles.  This module bridges the gap using:

  1. Exact title match (case-insensitive strip)
  2. Token overlap score >= 0.4  (Jaccard on word sets)

No LLM, no external calls — pure Python, deterministic, testable.

Usage:
    story_id_map = await build_story_id_map(db, project_id, workbook_summary)
    # {"User story -1.1 User Registration…": 42, …}
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.models.user_story import UserStory

logger = logging.getLogger(__name__)


def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two strings."""
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _match_story_name(
    excel_name: str,
    db_stories: List[Dict[str, Any]],
    *,
    threshold: float = 0.4,
) -> Optional[int]:
    """Return the user_story_id that best matches the given Excel story name.

    Tries exact match first, then token overlap.  Returns None if no match
    exceeds the threshold.

    Args:
        excel_name:  Story name from the Excel summary/sheet.
        db_stories:  List of {"id": int, "title": str} rows from the DB.
        threshold:   Minimum Jaccard score to accept as a match.

    Returns:
        The matched user_story_id, or None.
    """
    name_lc = excel_name.strip().lower()

    # 1. Exact match (case-insensitive)
    for row in db_stories:
        if row["title"].strip().lower() == name_lc:
            return row["id"]

    # 2. Token overlap
    best_id: Optional[int] = None
    best_score = 0.0
    for row in db_stories:
        score = _jaccard(excel_name, row["title"])
        if score > best_score:
            best_score = score
            best_id = row["id"]

    if best_score >= threshold:
        logger.debug(
            "[ExcelStoryMapper] '%s' → story_id=%s (score=%.2f)", excel_name, best_id, best_score
        )
        return best_id

    logger.debug("[ExcelStoryMapper] No match for '%s' (best=%.2f)", excel_name, best_score)
    return None


async def build_story_id_map(
    db: AsyncSession,
    project_id: int,
    excel_story_names: List[str],
) -> Dict[str, int]:
    """Build a mapping of Excel story names to DB user_story_id values.

    Queries all user_stories for the given project, then matches each
    Excel story name using exact-then-token-overlap matching.

    Args:
        db:                AsyncSession for the current request.
        project_id:        The target project.
        excel_story_names: List of story names from the Excel workbook
                           (summary tab or sheet names).

    Returns:
        {excel_story_name: user_story_id} for successfully matched names.
        Unmatched names are omitted; the caller decides whether to fail or skip.
    """
    if not excel_story_names:
        return {}

    result = await db.execute(
        select(UserStory.id, UserStory.title)
        .where(UserStory.project_id == project_id)
    )
    db_stories = [{"id": row.id, "title": row.title} for row in result]

    if not db_stories:
        logger.warning(
            "[ExcelStoryMapper] Project %s has no user stories — all Excel stories will be unmapped.",
            project_id,
        )
        return {}

    mapping: Dict[str, int] = {}
    for name in excel_story_names:
        if not name or not name.strip():
            continue
        story_id = _match_story_name(name, db_stories)
        if story_id is not None:
            mapping[name] = story_id
        else:
            logger.info("[ExcelStoryMapper] Unmatched story: %r", name)

    matched = len(mapping)
    total = len(excel_story_names)
    logger.info(
        "[ExcelStoryMapper] Matched %d/%d Excel stories for project %d.",
        matched,
        total,
        project_id,
    )
    return mapping
