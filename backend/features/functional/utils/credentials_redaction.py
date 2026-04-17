"""Strip project username/password substrings from step text and agent logs before persistence."""

from typing import Any, Dict, List, Optional

from features.functional.utils.step_result_display import normalize_display_field

REDACT_TOKEN = "••••••••"

_STEP_STRING_KEYS = frozenset(
    {
        "actual_result",
        "adaptation",
        "description",
        "value",
        "expected_result",
        "target",
        "summary",
        "message",
        "error",
        "error_message",
        "notes",
    }
)

_LOG_STRING_KEYS = frozenset({"description", "adaptation", "message"})


def redact_known_credentials(
    text: Optional[str],
    *,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> Optional[str]:
    if not text:
        return text
    secrets: List[str] = []
    if password:
        p = password.strip()
        if p:
            secrets.append(p)
    if username:
        u = username.strip()
        if len(u) >= 2:
            secrets.append(u)
    if not secrets:
        return text
    secrets.sort(key=len, reverse=True)
    out = text
    seen: set[str] = set()
    for s in secrets:
        if s in seen:
            continue
        seen.add(s)
        out = out.replace(s, REDACT_TOKEN)
    return out


def redact_step_dict(
    step: Dict[str, Any],
    username: Optional[str],
    password: Optional[str],
) -> Dict[str, Any]:
    if not step:
        return step
    out = dict(step)
    for k in _STEP_STRING_KEYS:
        if k not in out:
            continue
        v = out[k]
        text = normalize_display_field(v)
        out[k] = redact_known_credentials(text, username=username, password=password) or ""
    return out


def redact_agent_logs_list(
    logs: Optional[List[Any]],
    username: Optional[str],
    password: Optional[str],
) -> Optional[List[Any]]:
    if not logs:
        return logs
    out: List[Any] = []
    for entry in logs:
        if not isinstance(entry, dict):
            out.append(entry)
            continue
        e = dict(entry)
        for k in _LOG_STRING_KEYS:
            if k not in e:
                continue
            v = e[k]
            text = normalize_display_field(v)
            e[k] = redact_known_credentials(text, username=username, password=password) or ""
        out.append(e)
    return out
