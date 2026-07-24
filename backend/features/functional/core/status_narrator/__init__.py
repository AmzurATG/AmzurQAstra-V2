"""Status Narrator — honest infra vs product-failure messaging.

Ensures rate-limit / circuit / missing-verdict cases never look like
"failed 0/10 with no evidence".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


USER_MESSAGES = {
    "rate": "AI service is busy (rate limited). This case was not executed against the app.",
    "timeout": "AI service timed out. This case was not fully executed.",
    "server": "AI service is temporarily unavailable. This case was not executed.",
    "budget": "AI service budget exhausted. Execution paused — not an application failure.",
    "auth": "AI service authentication failed. Check API configuration.",
    "missing_verdict_json": "Could not verify results (AI response incomplete). Not a confirmed app failure.",
    "missing_screenshots": "No screenshots were captured. Re-run required for evidence.",
    "wallclock_timeout": "Case exceeded the time limit before finishing.",
    "circuit_open": "AI service cooling down. Waiting to retry — not an application failure.",
    "default": "Execution blocked by infrastructure. Not recorded as an application test failure.",
}


def user_message_for(error_kind: Optional[str], *, error: Optional[str] = None) -> str:
    kind = (error_kind or "").lower().strip()
    if kind in USER_MESSAGES:
        return USER_MESSAGES[kind]
    err = (error or "").lower()
    for key in ("rate", "timeout", "budget", "circuit", "screenshot", "verdict"):
        if key in kind or key in err:
            if key == "circuit":
                return USER_MESSAGES["circuit_open"]
            if key == "screenshot":
                return USER_MESSAGES["missing_screenshots"]
            if key == "verdict":
                return USER_MESSAGES["missing_verdict_json"]
            return USER_MESSAGES.get(key, USER_MESSAGES["default"])
    return USER_MESSAGES["default"]


def infra_step_stubs(
    original_steps: Sequence[Dict[str, Any]],
    *,
    error_kind: Optional[str] = None,
    error: Optional[str] = None,
    summary: str = "",
) -> List[Dict[str, Any]]:
    """Build full step list so UI never shows empty 0/N without explanation."""
    msg = user_message_for(error_kind, error=error)
    detail = summary.strip() or msg
    out: List[Dict[str, Any]] = []
    for s in original_steps:
        stub = dict(s) if isinstance(s, dict) else {"step_number": len(out) + 1}
        stub.update(
            {
                "status": "error",
                "actual_result": detail,
                "adaptation": None,
                "infra_blocked": True,
            }
        )
        out.append(stub)
    if not out:
        out.append(
            {
                "step_number": 1,
                "status": "error",
                "actual_result": detail,
                "description": "Execution blocked",
                "infra_blocked": True,
            }
        )
    return out


def narrate_case_result(result: Dict[str, Any], original_steps: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize infra/error payloads for persistence + UI."""
    out = dict(result)
    infra = bool(out.get("infra_error"))
    kind = out.get("error_kind")
    overall = str(out.get("overall") or out.get("status") or "").lower()

    if infra or overall == "error" or kind in (
        "rate",
        "timeout",
        "server",
        "budget",
        "auth",
        "missing_verdict_json",
        "missing_screenshots",
        "wallclock_timeout",
    ):
        steps = list(out.get("step_results") or [])
        if not steps or all(
            not (s.get("actual_result") or "").strip()
            for s in steps
            if isinstance(s, dict)
        ):
            out["step_results"] = infra_step_stubs(
                original_steps,
                error_kind=str(kind) if kind else None,
                error=str(out.get("error") or ""),
                summary=str(out.get("summary") or ""),
            )
        msg = user_message_for(str(kind) if kind else None, error=str(out.get("error") or ""))
        out["error"] = out.get("error") or (str(kind) if kind else "infra_error")
        out["user_message"] = msg
        out["summary"] = out.get("summary") or msg
        # Keep overall as error (not failed) so UI can distinguish
        out["overall"] = "error"
        out["status"] = "error"
        out["infra_error"] = True
    return out


def live_status_banner(gate_snapshot: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """User-facing live banner while waiting / degraded."""
    if not gate_snapshot:
        return None
    br = gate_snapshot.get("breaker") or {}
    state = str(br.get("state") or "")
    kind = br.get("last_kind") or "unknown"
    cd = float(br.get("cooldown_remaining_s") or 0)
    if state == "open":
        return {
            "level": "warning",
            "message": (
                f"AI service cooling down ({kind}). "
                f"Waiting ~{int(cd)}s — cases will resume automatically. "
                "This is not an application failure."
            ),
        }
    if state == "degraded":
        return {
            "level": "info",
            "message": (
                "AI service running in degraded mode (fallback models). "
                "Results remain valid; execution may be slightly slower."
            ),
        }
    return None
