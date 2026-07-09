"""Helpers for summarizing a finished test run for UI + PDF."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def pass_rate(passed: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round(100.0 * passed / total))


def majority_passed(passed: int, failed: int, total: Optional[int] = None) -> bool:
    """True when most executed cases passed (user-facing 'not a failed run')."""
    t = total if total is not None else (passed + failed)
    if t <= 0:
        return False
    return passed > failed and pass_rate(passed, t) >= 50


def finalize_run_status(
    *,
    cancelled: bool,
    passed: int,
    failed: int,
    total: Optional[int] = None,
) -> str:
    """
    Return canonical TestRunStatus value string.

    A run with a clear majority of passes is stored as ``passed`` even if some
    cases failed — failures remain visible in counts and the Failures Digest.
    """
    if cancelled:
        return "cancelled"
    t = total if total is not None else (passed + failed)
    if t <= 0:
        return "error"
    if majority_passed(passed, failed, t):
        return "passed"
    if failed > 0:
        return "failed"
    if passed > 0:
        return "passed"
    return "error"


def display_run_status(
    status: str,
    *,
    passed: int = 0,
    failed: int = 0,
    total: int = 0,
) -> Dict[str, Any]:
    """
    UI-facing status label/tone. Historical rows stored as ``failed`` but with a
    majority pass still show as mostly-passed.
    """
    raw = (status or "").lower()
    t = total or (passed + failed)
    rate = pass_rate(passed, t) if t else 0

    if raw in ("running", "pending", "cancelled", "error"):
        return {
            "status": raw,
            "label": raw.replace("_", " ").title(),
            "tone": "neutral" if raw in ("pending", "cancelled") else ("danger" if raw == "error" else "info"),
            "pass_rate": rate,
        }

    if majority_passed(passed, failed, t):
        label = "Passed" if failed == 0 else f"Passed ({failed} failed)"
        return {
            "status": "passed",
            "label": label,
            "tone": "success",
            "pass_rate": rate,
            "has_failures": failed > 0,
        }

    if failed > 0 or raw == "failed":
        return {
            "status": "failed",
            "label": "Failed",
            "tone": "danger",
            "pass_rate": rate,
            "has_failures": True,
        }

    return {
        "status": "passed",
        "label": "Passed",
        "tone": "success",
        "pass_rate": rate,
        "has_failures": False,
    }


def report_outcome_headline(passed: int, failed: int, total: int) -> Tuple[str, str]:
    """Return (headline, tone) for PDF cover."""
    rate = pass_rate(passed, total)
    if total <= 0:
        return ("No tests executed.", "danger")
    if failed == 0:
        return (f"All {total} tests passed ({rate}%).", "success")
    if majority_passed(passed, failed, total):
        return (
            f"Mostly passed - {passed}/{total} passed ({rate}%). "
            f"{failed} case(s) need triage (see Failures Digest).",
            "success",
        )
    return (
        f"Run failed - {passed}/{total} passed ({rate}%). "
        f"{failed} case(s) failed.",
        "danger",
    )
