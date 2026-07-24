"""Accuracy types."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, TypedDict


class VerdictSource(str, Enum):
    PARSED = "parsed"
    FALLBACK = "fallback"
    INCONCLUSIVE = "inconclusive"


class EvidenceQuality(str, Enum):
    OK = "ok"
    MISSING_SCREENSHOTS = "missing_screenshots"
    MISSING_VERDICT_JSON = "missing_verdict_json"
    VERDICT_CONFLICT = "verdict_conflict"


class FinalStatusDecision(TypedDict, total=False):
    status: str
    ui_override: bool
    executor_status: Optional[str]
    error_kind: Optional[str]
    error: Optional[str]
    ui_validation: Dict[str, Any]
