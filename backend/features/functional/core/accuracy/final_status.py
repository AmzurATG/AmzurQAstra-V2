"""Resolve executor vs UI validator final status."""
from __future__ import annotations

from typing import Any, Dict, Optional

from config import settings
from features.functional.core.accuracy.types import EvidenceQuality, FinalStatusDecision


def resolve_final_status(
    *,
    executor_status: str,
    ui_verdict: Optional[str] = None,
    ui_confidence: Optional[float] = None,
    ui_payload: Optional[Dict[str, Any]] = None,
    has_screenshots: bool = True,
) -> FinalStatusDecision:
    exec_st = (executor_status or "error").lower()
    base: FinalStatusDecision = {
        "status": exec_st,
        "ui_override": False,
        "executor_status": exec_st,
        "ui_validation": dict(ui_payload or {}),
    }
    if not has_screenshots or not ui_verdict:
        return base
    ui_st = str(ui_verdict).lower().strip()
    if ui_st not in ("passed", "failed", "inconclusive"):
        return base
    conf = float(ui_confidence if ui_confidence is not None else 0.0)
    threshold = float(getattr(settings, "UI_VALIDATION_CONFIDENCE", 0.75) or 0.75)
    if ui_st == "inconclusive" or ui_st == exec_st:
        return base
    if conf >= threshold and ui_st in ("passed", "failed"):
        return {
            "status": ui_st,
            "ui_override": True,
            "executor_status": exec_st,
            "ui_validation": dict(ui_payload or {}),
        }
    return {
        "status": "error",
        "ui_override": False,
        "executor_status": exec_st,
        "error_kind": EvidenceQuality.VERDICT_CONFLICT.value,
        "error": EvidenceQuality.VERDICT_CONFLICT.value,
        "ui_validation": dict(ui_payload or {}),
    }
