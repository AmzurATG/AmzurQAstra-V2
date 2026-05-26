"""Write browser screenshots to configured storage backend (local / S3 / Supabase)."""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings
from common.utils.logger import logger
from features.functional.core.storage import get_storage_adapter


def ensure_screenshots_dir() -> Path:
    d = Path(settings.SCREENSHOTS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


async def save_screenshot_b64(b64: str, run_id: str, tc_id: int, step: int) -> Optional[str]:
    try:
        ts = datetime.utcnow().strftime("%H%M%S%f")
        fname = f"tr_{run_id[:8]}_tc{tc_id}_s{step:02d}_{ts}.png"
        data = base64.b64decode(b64)

        if settings.STORAGE_TYPE == "local":
            # Save locally for static serving
            d = ensure_screenshots_dir()
            (d / fname).write_bytes(data)
        else:
            # Save to configured remote storage only (Supabase / S3)
            storage = get_storage_adapter()
            await storage.save(data, fname, "image/png", subdirectory="screenshots", preserve_filename=True)

        return f"/screenshots/{fname}"
    except Exception as exc:
        logger.warning(f"[ScreenshotStore] Screenshot save failed: {exc}")
        return None
