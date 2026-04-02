"""Screenshot path resolution for test results (local files under SCREENSHOTS_DIR)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from features.functional.db.models.test_result import TestResult


def _resolve_screenshot_file(filename: str) -> Optional[Path]:
    """Single-segment filename only; must exist under SCREENSHOTS_DIR."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return None
    if Path(filename).name != filename:
        return None
    lower = filename.lower()
    if not lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return None
    base = Path(settings.SCREENSHOTS_DIR).resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    if not target.is_file():
        return None
    return target


async def get_primary_screenshot_file(
    db: AsyncSession, run_id: int, result_id: int
) -> Optional[Path]:
    """Primary failure/summary screenshot for a result (validates test_run_id)."""
    row = await db.execute(
        select(TestResult).where(
            TestResult.id == result_id,
            TestResult.test_run_id == run_id,
        )
    )
    tr = row.scalar_one_or_none()
    if not tr or not tr.screenshot_path:
        return None
    return _resolve_screenshot_file(Path(tr.screenshot_path).name)


async def get_authorized_screenshot_file(
    db: AsyncSession, run_id: int, result_id: int, filename: str
) -> Optional[Path]:
    row = await db.execute(
        select(TestResult).where(
            TestResult.id == result_id,
            TestResult.test_run_id == run_id,
        )
    )
    tr = row.scalar_one_or_none()
    if not tr:
        return None

    allowed: set[str] = set()
    if tr.screenshot_path:
        allowed.add(Path(tr.screenshot_path).name)
    for entry in tr.agent_logs or []:
        p = entry.get("screenshot_path")
        if isinstance(p, str) and p.strip():
            allowed.add(Path(p).name)
    for s in tr.step_results or []:
        p = s.get("screenshot_path")
        if isinstance(p, str) and p.strip():
            allowed.add(Path(p).name)
    if filename not in allowed:
        return None

    return _resolve_screenshot_file(filename)
