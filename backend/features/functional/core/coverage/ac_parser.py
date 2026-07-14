"""
Deterministic acceptance-criteria parser.

Splits raw AC text into atomic AcCondition objects without calling an LLM.
Used as the fast path by AcDecompositionService.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


_VALIDATION_RE = re.compile(
    r"\b(must\s+(not|reject|prevent|block|deny)|invalid|error|reject|"
    r"cannot|should\s+not|fails?|forbidden|unauthorized)\b",
    re.IGNORECASE,
)
_BOUNDARY_RE = re.compile(
    r"\b(\d+|max(?:imum)?|min(?:imum)?|length|limit|at\s+least|at\s+most|"
    r"between|range|characters?|seconds?|minutes?|hours?|days?)\b",
    re.IGNORECASE,
)
_FIELD_RE = re.compile(
    r"\b(email|password|username|phone|name|token|otp|code|amount|"
    r"date|url|address|role|status|title|description)\b",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(
    r"^\s*(?:[-*•]|\d+[.)]|AC[-_]?\d+[:.)]?)\s*",
    re.IGNORECASE,
)


@dataclass
class AcCondition:
    """One independently testable acceptance condition."""

    id: str
    text: str
    has_validation_rule: bool = False
    has_numeric_boundary: bool = False
    input_fields: List[str] = field(default_factory=list)
    scenario_hints: List[str] = field(default_factory=lambda: ["positive"])


def _split_lines(ac_text: str) -> List[str]:
    """Split AC text into candidate condition lines."""
    chunks: List[str] = []
    for raw in re.split(r"[\n\r]+", ac_text):
        line = _BULLET_RE.sub("", raw).strip()
        if not line:
            continue
        # Further split compound "and" clauses when both sides look like conditions
        parts = re.split(r"\s+;\s+|\s+AND\s+", line, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip(" .;")
            if len(part) >= 8:
                chunks.append(part)
    return chunks


def _hints_for(text: str, has_validation: bool, has_boundary: bool) -> List[str]:
    hints = ["positive"]
    if has_validation:
        hints.append("negative")
    if has_boundary:
        hints.append("boundary")
    lower = text.lower()
    if any(w in lower for w in ("edge", "corner", "unusual", "empty", "null")):
        if "edge" not in hints:
            hints.append("edge")
    return hints


def parse(ac_text: str) -> List[AcCondition]:
    """
    Parse raw acceptance criteria into structured AcCondition objects.

    Returns an empty list when the text yields no usable lines (caller
    should fall back to a generic condition).
    """
    text = (ac_text or "").strip()
    if not text:
        return []

    lines = _split_lines(text)
    if not lines:
        # Single-paragraph AC — treat the whole block as one condition
        lines = [text[:500]]

    conditions: List[AcCondition] = []
    for i, line in enumerate(lines, start=1):
        has_validation = bool(_VALIDATION_RE.search(line))
        has_boundary = bool(_BOUNDARY_RE.search(line))
        fields = sorted({m.group(1).lower() for m in _FIELD_RE.finditer(line)})
        conditions.append(
            AcCondition(
                id=f"AC-{i}",
                text=line[:500],
                has_validation_rule=has_validation,
                has_numeric_boundary=has_boundary,
                input_fields=fields,
                scenario_hints=_hints_for(line, has_validation, has_boundary),
            )
        )
    return conditions
