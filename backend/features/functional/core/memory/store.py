"""Lightweight JSON memory of run patterns (slow cases, desync, recon failures)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings


def _memory_root() -> Path:
    # App root is parent of backend/ when SCREENSHOTS_DIR is under app root
    shots = Path(getattr(settings, "SCREENSHOTS_DIR", "") or ".")
    root = shots.parent if shots.name == "screenshots" else shots.parent
    path = root / "run_memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def memory_path(project_id: int) -> Path:
    return _memory_root() / f"{int(project_id)}.json"


def load_memory(project_id: int) -> Dict[str, Any]:
    path = memory_path(project_id)
    if not path.is_file():
        return {"project_id": project_id, "hints": [], "events": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"project_id": project_id, "hints": [], "events": []}


def save_memory(project_id: int, data: Dict[str, Any]) -> None:
    path = memory_path(project_id)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def append_event(project_id: int, event: Dict[str, Any], *, hint: Optional[str] = None) -> Dict[str, Any]:
    data = load_memory(project_id)
    events: List[Dict[str, Any]] = list(data.get("events") or [])
    events.append(event)
    data["events"] = events[-200:]
    if hint:
        hints: List[str] = list(data.get("hints") or [])
        if hint not in hints:
            hints.append(hint)
        data["hints"] = hints[-50:]
    save_memory(project_id, data)
    return data


def planner_hints(project_id: int, *, limit: int = 8) -> List[str]:
    data = load_memory(project_id)
    return list(data.get("hints") or [])[-limit:]


def format_memory_prompt_hint(project_id: int) -> str:
    hints = planner_hints(project_id)
    if not hints:
        return ""
    lines = ["MEMORY HINTS (from prior runs — soft guidance):"]
    for h in hints:
        lines.append(f"- {h}")
    return "\n".join(lines)
