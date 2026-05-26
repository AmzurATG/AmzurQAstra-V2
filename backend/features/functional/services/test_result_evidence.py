"""Screenshot path resolution for test results (local files or remote storage)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

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


def _validate_screenshot_filename(filename: str) -> bool:
    """Validate filename without requiring local existence."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return False
    if Path(filename).name != filename:
        return False
    lower = filename.lower()
    return lower.endswith((".png", ".jpg", ".jpeg", ".webp"))


async def _resolve_screenshot(filename: str) -> Union[Path, bytes, None]:
    """Resolve a screenshot: local Path if it exists, otherwise bytes from remote storage."""
    # Try local first
    local = _resolve_screenshot_file(filename)
    if local is not None:
        return local
    # Validate filename before remote lookup
    if not _validate_screenshot_filename(filename):
        return None
    # Try remote storage (Supabase / S3)
    if settings.STORAGE_TYPE != "local":
        from features.functional.core.storage import get_storage_adapter
        storage = get_storage_adapter()
        data = await storage.get(f"screenshots/{filename}")
        if data is not None:
            return data
    return None


async def get_primary_screenshot_file(
    db: AsyncSession, run_id: int, result_id: int
) -> Union[Path, bytes, None]:
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
    return await _resolve_screenshot(Path(tr.screenshot_path).name)


async def get_authorized_screenshot_file(
    db: AsyncSession, run_id: int, result_id: int, filename: str
) -> Union[Path, bytes, None]:
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

    return await _resolve_screenshot(filename)
