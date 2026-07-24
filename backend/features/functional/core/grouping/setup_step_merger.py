"""Setup-step merge for shared-login groups.

Skipped login/navigate steps are still reported with full detail so the user
sees a complete step list. Shared setup is marked passed (not failed/skipped
in the UI) and can inherit screenshots from the case that actually logged in.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

_SETUP = (
    re.compile(r"\b(log\s*in|login|sign\s*in)\b", re.I),
    re.compile(r"\b(enter the url|launch|navigate to (the )?(app|url|users?|user tab))\b", re.I),
)

# User-facing copy — avoid "shared group" / orchestration jargon.
SHARED_SETUP_RESULT = "Already signed in — login completed earlier in this session."
SHARED_SETUP_LEGACY = "Shared group setup"


def is_setup_step(step: Dict[str, Any]) -> bool:
    action = str(step.get("action") or "").lower()
    desc = str(step.get("description") or "")
    if action in ("navigate", "goto", "login", "signin"):
        return True
    return any(p.search(desc) for p in _SETUP)


def is_shared_setup_result(step: Dict[str, Any]) -> bool:
    if bool(step.get("shared_setup")):
        return True
    actual = str(step.get("actual_result") or "")
    return actual in (SHARED_SETUP_RESULT, SHARED_SETUP_LEGACY)


def leading_setup_count(steps: Sequence[Dict[str, Any]]) -> int:
    n = 0
    for s in steps:
        if is_setup_step(s):
            n += 1
        else:
            break
    return n


def prepare_steps_for_shared_session(
    steps: Sequence[Dict[str, Any]],
    *,
    session_warm: bool,
    donor_setup_steps: Optional[Sequence[Dict[str, Any]]] = None,
    donor_screenshot_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    """Return (steps_to_run, skipped_setup_stubs, session_context).

    Skipped stubs keep full original step text and inherit donor evidence when
    available so the expanded case view still shows login detail + screenshots.
    """
    original = [dict(s) for s in steps]
    if not session_warm or not original:
        return original, [], None
    n = leading_setup_count(original)
    if n >= len(original):
        n = max(0, len(original) - 1)
    if n <= 0:
        return original, [], "already_authenticated"

    donor_by_num = {
        s.get("step_number"): dict(s)
        for s in (donor_setup_steps or [])
        if isinstance(s, dict)
    }
    donor_ordered = [dict(s) for s in (donor_setup_steps or []) if isinstance(s, dict)]

    skipped: List[Dict[str, Any]] = []
    for i, s in enumerate(original[:n]):
        stub = dict(s)
        donor = donor_by_num.get(s.get("step_number"))
        if donor is None and i < len(donor_ordered):
            donor = donor_ordered[i]
        actual = SHARED_SETUP_RESULT
        shot = donor_screenshot_path
        if donor:
            donor_actual = str(donor.get("actual_result") or "").strip()
            if donor_actual and donor_actual not in (SHARED_SETUP_RESULT, SHARED_SETUP_LEGACY):
                actual = f"{SHARED_SETUP_RESULT} Prior result: {donor_actual[:400]}"
            shot = donor.get("screenshot_path") or shot
            if donor.get("description") and not stub.get("description"):
                stub["description"] = donor.get("description")
            if donor.get("expected_result") and not stub.get("expected_result"):
                stub["expected_result"] = donor.get("expected_result")
        stub.update(
            status="passed",
            actual_result=actual,
            shared_setup=True,
            adaptation=None,
            screenshot_path=shot,
        )
        skipped.append(stub)
    return original[n:], skipped, "already_authenticated"


def merge_step_results_with_skipped_setup(
    original_steps: Sequence[Dict[str, Any]],
    skipped_setup: Sequence[Dict[str, Any]],
    run_step_results: Sequence[Dict[str, Any]],
    *,
    overall_status: Optional[str] = None,
    summary: str = "",
) -> List[Dict[str, Any]]:
    skipped_nums = {s.get("step_number") for s in skipped_setup}
    by_num = {s.get("step_number"): dict(s) for s in run_step_results if isinstance(s, dict)}
    ordered = [dict(s) for s in run_step_results if isinstance(s, dict)]
    remaining = [s.get("step_number") for s in original_steps if s.get("step_number") not in skipped_nums]
    pos = {num: ordered[i] for i, num in enumerate(remaining) if i < len(ordered)}
    overall = (overall_status or "").lower()
    out: List[Dict[str, Any]] = []
    for s_orig in original_steps:
        num = s_orig.get("step_number")
        if num in skipped_nums:
            stub = next((x for x in skipped_setup if x.get("step_number") == num), None)
            if stub:
                out.append(dict(stub))
            else:
                out.append(
                    {
                        **s_orig,
                        "status": "passed",
                        "actual_result": SHARED_SETUP_RESULT,
                        "shared_setup": True,
                    }
                )
            continue
        s_res = by_num.get(num) or pos.get(num) or {}
        status = s_res.get("status")
        actual = s_res.get("actual_result")
        if not status or status == "skipped":
            if overall == "passed":
                status, actual = "passed", actual or (summary[:500] or "Verified under existing session")
            elif overall == "failed":
                status, actual = "failed", actual or (summary[:500] or "Failed under existing session")
            else:
                status = status or "skipped"
        merged = {
            **s_orig,
            "status": status,
            "actual_result": actual,
            "adaptation": s_res.get("adaptation"),
        }
        if s_res.get("screenshot_path"):
            merged["screenshot_path"] = s_res.get("screenshot_path")
        out.append(merged)
    return out


def extract_setup_donor_evidence(
    step_results: Optional[Sequence[Dict[str, Any]]],
    agent_logs: Optional[Sequence[Dict[str, Any]]] = None,
    screenshot_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Pull setup-step results + a representative screenshot from a warm-session donor case."""
    steps = [dict(s) for s in (step_results or []) if isinstance(s, dict)]
    setup = [s for s in steps if is_setup_step(s) or is_shared_setup_result(s)]
    if not setup:
        # Fall back to leading steps that look like navigate/login by description
        n = leading_setup_count(steps)
        setup = steps[:n] if n else []

    shot = screenshot_path
    for s in setup:
        if s.get("screenshot_path"):
            shot = s.get("screenshot_path")
            break
    if not shot:
        for log in agent_logs or []:
            if isinstance(log, dict) and log.get("screenshot_path") and log.get("evidence", True):
                shot = log.get("screenshot_path")
                break
    if not shot:
        for log in agent_logs or []:
            if isinstance(log, dict) and log.get("screenshot_path"):
                shot = log.get("screenshot_path")
                break

    # Attach donor shot onto setup stubs that lack one
    if shot:
        for s in setup:
            s.setdefault("screenshot_path", shot)
    return setup, shot


def compute_step_display_counts(step_results: Optional[Sequence[Dict[str, Any]]]) -> Dict[str, int]:
    """Honest step counts for the UI — include shared setup as completed steps."""
    steps = list(step_results or [])
    setup_shared = sum(1 for s in steps if is_shared_setup_result(s))
    passed = sum(1 for s in steps if str(s.get("status") or "").lower() == "passed")
    failed = sum(1 for s in steps if str(s.get("status") or "").lower() == "failed")
    return {
        # Show full case step list (setup included) so users never see "2/2 +2 setup skipped"
        "steps_total": len(steps),
        "steps_passed": passed,
        "steps_failed": failed,
        "setup_skipped_count": setup_shared,
        "steps_all_total": len(steps),
    }
