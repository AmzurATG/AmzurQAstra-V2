"""Plain-language descriptions for browser-use action payloads."""
from __future__ import annotations

from typing import Any


def humanize_action_dict(d: dict) -> str:
    if not d:
        return "Working on the page…"
    for key, val in d.items():
        if not isinstance(val, dict):
            continue
        k = key.lower()
        if k in ("click", "click_element"):
            # Prefer a human-readable label or placeholder over the raw DOM index
            label = (
                val.get("label")
                or val.get("text")
                or val.get("placeholder")
                or val.get("aria_label")
                or val.get("name")
                or ""
            )
            label = str(label).strip()[:60]
            return f"Clicked '{label}'" if label else "Clicked an element"
        if k in ("input", "input_text"):
            # Show what field was targeted by name/placeholder, not by DOM index
            field = (
                val.get("label")
                or val.get("placeholder")
                or val.get("name")
                or val.get("aria_label")
                or ""
            )
            field = str(field).strip()[:60]
            return f"Entered text into '{field}'" if field else "Entered text in a field"
        if k in ("navigate", "go_to_url", "goto"):
            url = (val.get("url") or "")[:80]
            return f"Opened: {url}" if url else "Opened a page"
        if k in ("scroll", "scroll_down", "scroll_up"):
            return "Scrolled the page"
        if k in ("done", "complete"):
            msg = (val.get("text") or val.get("message") or "")[:200]
            return f"Finished — {msg}" if msg else "Finished"
        if k in ("go_back",):
            return "Went back"
        if k in ("wait", "wait_for"):
            return "Waited for the page"
        if k in ("extract", "extract_content"):
            return "Read content from the page"
        if k == "send_keys":
            return "Sent keyboard input"
    return "Worked on the page"


def action_description_from_output(output: Any) -> str:
    try:
        if output and hasattr(output, "action") and output.action:
            parts = []
            for act in output.action:
                dump = act.model_dump(exclude_none=True) if hasattr(act, "model_dump") else {}
                parts.append(humanize_action_dict(dump))
            return " · ".join(parts) if parts else "Working…"
    except Exception:
        pass
    return "Working…"
