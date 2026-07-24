"""UI validation agent schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UiStepCheck(BaseModel):
    step: int
    status: str = "inconclusive"  # passed | failed | inconclusive
    evidence: Optional[str] = None
    why: Optional[str] = None


class UiValidationResult(BaseModel):
    ui_verdict: str = "inconclusive"  # passed | failed | inconclusive
    confidence: float = 0.0
    step_checks: List[UiStepCheck] = Field(default_factory=list)
    ui_observations: List[str] = Field(default_factory=list)
    disagrees_with_executor: bool = False
    raw_summary: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return self.model_dump()
