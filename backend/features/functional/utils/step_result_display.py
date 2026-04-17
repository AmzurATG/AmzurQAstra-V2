"""Normalize step/log text fields to readable plain strings (no raw JSON blobs)."""

import json
from typing import Any

_MAX_DEPTH = 6
_MAX_LIST = 40
_MAX_DICT_ITEMS = 50


def _flatten_value(value: Any, depth: int = 0) -> str:
    if depth > _MAX_DEPTH:
        return "…"
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts: list[str] = []
        for i, (k, v) in enumerate(value.items()):
            if i >= _MAX_DICT_ITEMS:
                parts.append("…")
                break
            parts.append(f"{k}: {_flatten_value(v, depth + 1)}")
        return "; ".join(parts)
    if isinstance(value, list):
        items = [_flatten_value(x, depth + 1) for x in value[:_MAX_LIST]]
        if len(value) > _MAX_LIST:
            items.append("…")
        return "; ".join(items)
    return str(value)


def normalize_display_field(value: Any) -> str:
    """Turn None, dict, list, or JSON-looking strings into readable plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        s = value.strip()
        if len(s) >= 2 and s[0] in "{[" and s[-1] in "]}":
            try:
                parsed = json.loads(s)
                return normalize_display_field(parsed)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        return value.strip() if value else ""
    return _flatten_value(value)
