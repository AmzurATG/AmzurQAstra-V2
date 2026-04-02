"""Write browser screenshots to local SCREENSHOTS_DIR (S3-ready seam later)."""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings
from common.utils.logger import logger


def ensure_screenshots_dir() -> Path:
    d = Path(settings.SCREENSHOTS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_screenshot_b64(b64: str, run_id: str, tc_id: int, step: int) -> Optional[str]:
    try:
        ts = datetime.utcnow().strftime("%H%M%S%f")
        fname = f"tr_{run_id[:8]}_tc{tc_id}_s{step:02d}_{ts}.png"
        d = ensure_screenshots_dir()
        (d / fname).write_bytes(base64.b64decode(b64))
        return f"/screenshots/{fname}"
    except Exception as exc:
        logger.warning(f"[ScreenshotStore] Screenshot save failed: {exc}")
        return None
