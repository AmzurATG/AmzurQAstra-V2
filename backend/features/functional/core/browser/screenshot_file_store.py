"""Write browser screenshots to local SCREENSHOTS_DIR (S3-ready seam later).

Adds content-hash dedup (skip identical consecutive frames, common on wait/no-op
steps) and a light lossless PNG optimize to cut disk without losing evidence.
"""
from __future__ import annotations

import base64
import hashlib
import io
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from config import settings
from common.utils.logger import logger

# Last saved screenshot per test-case key -> (content_hash, stored_path).
# Lets consecutive identical frames reuse the same file instead of rewriting.
_last_shot: Dict[str, tuple[str, str]] = {}
_lock = threading.Lock()


def ensure_screenshots_dir() -> Path:
    d = Path(settings.SCREENSHOTS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _optimize_png(raw: bytes) -> bytes:
    """Lossless-ish PNG optimize; returns original bytes on any failure."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as im:
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            out = buf.getvalue()
            return out if out and len(out) < len(raw) else raw
    except Exception:
        return raw


def save_screenshot_b64(
    b64: str,
    run_id: str,
    tc_id: int,
    step: int,
    *,
    dedup: bool = True,
    optimize: bool = True,
) -> Optional[str]:
    try:
        raw = base64.b64decode(b64)
        key = f"{run_id[:8]}:{tc_id}"
        digest = hashlib.sha1(raw).hexdigest()

        if dedup:
            with _lock:
                prev = _last_shot.get(key)
            if prev and prev[0] == digest:
                # Identical to the previous frame for this case — reuse the file.
                return prev[1]

        data = _optimize_png(raw) if optimize else raw
        ts = datetime.utcnow().strftime("%H%M%S%f")
        fname = f"tr_{run_id[:8]}_tc{tc_id}_s{step:02d}_{ts}.png"
        d = ensure_screenshots_dir()
        (d / fname).write_bytes(data)
        path = f"/screenshots/{fname}"

        if dedup:
            with _lock:
                _last_shot[key] = (digest, path)
        return path
    except Exception as exc:
        logger.warning(f"[ScreenshotStore] Screenshot save failed: {exc}")
        return None
