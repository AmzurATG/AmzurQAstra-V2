"""
AC Parser — parses acceptance criteria text into structured AcCondition objects.

Provides deterministic parsing of AC text (Given/When/Then format) with
detection of validation rules and numeric boundaries.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AcCondition:
    """
    Represents a single acceptance criterion extracted from AC text.
    
    Attributes:
        id: Unique identifier for this condition (e.g., "AC-1")
        text: The full text of this acceptance criterion
        has_validation_rule: Whether this condition contains validation logic
        has_numeric_boundary: Whether this condition has numeric constraints
        input_fields: List of input field names mentioned in this condition
        scenario_hints: List of scenario types this condition suggests (e.g., "positive", "negative")
    """
    id: str
    text: str
    has_validation_rule: bool = False
    has_numeric_boundary: bool = False
    input_fields: List[str] = field(default_factory=list)
    scenario_hints: List[str] = field(default_factory=lambda: ["positive"])
    
    def to_dict(self) -> dict:
        """Convert condition to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "has_validation_rule": self.has_validation_rule,
            "has_numeric_boundary": self.has_numeric_boundary,
            "input_fields": self.input_fields,
            "scenario_hints": self.scenario_hints,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> AcCondition:
        """Create condition from dictionary."""
        return cls(
            id=data.get("id", "AC-0"),
            text=data.get("text", ""),
            has_validation_rule=data.get("has_validation_rule", False),
            has_numeric_boundary=data.get("has_numeric_boundary", False),
            input_fields=data.get("input_fields", []),
            scenario_hints=data.get("scenario_hints", ["positive"]),
        )


def parse(ac_text: str) -> List[AcCondition]:
    """
    Parse acceptance criteria text into structured conditions.
    
    Handles:
    - Given/When/Then (BDD) format
    - Numbered/bulleted lists
    - Simple paragraph text
    
    Args:
        ac_text: Raw acceptance criteria text
    
    Returns:
        List of AcCondition objects extracted from the text
    """
    if not ac_text or not ac_text.strip():
        return []
    
    conditions = []
    
    # Try BDD parsing first (Given/When/Then)
    bdd_conditions = _parse_bdd(ac_text)
    if bdd_conditions:
        return bdd_conditions
    
    # Try numbered/bulleted list parsing
    list_conditions = _parse_list(ac_text)
    if list_conditions:
        return list_conditions
    
    # Fall back to paragraph parsing
    para_conditions = _parse_paragraph(ac_text)
    return para_conditions


def _parse_bdd(text: str) -> List[AcCondition]:
    """Parse Given/When/Then (BDD) format."""
    # Pattern: Given ... When ... Then ...
    pattern = r"(?:Given|given)\s+(.+?)(?=\s+(?:When|when)|$)"
    given_match = re.search(pattern, text, re.IGNORECASE)
    
    if not given_match:
        return []
    
    conditions = []
    bdd_blocks = re.findall(
        r"(?:Given|When|Then|And|But)\s+(.+?)(?=\n|$)",
        text,
        re.IGNORECASE
    )
    
    for i, block in enumerate(bdd_blocks, start=1):
        block = block.strip()
        if not block:
            continue
        
        condition = _create_condition(block, f"AC-{i}")
        conditions.append(condition)
    
    return conditions


def _parse_list(text: str) -> List[AcCondition]:
    """Parse numbered or bulleted lists."""
    # Match numbered items (1., 2., etc.) or bullet points (-, *, •)
    pattern = r"^[\s]*(?:\d+\.|[-*•])\s+(.+?)$"
    matches = re.findall(pattern, text, re.MULTILINE)
    
    if len(matches) < 2:
        return []
    
    conditions = []
    for i, match in enumerate(matches, start=1):
        block = match.strip()
        if block:
            condition = _create_condition(block, f"AC-{i}")
            conditions.append(condition)
    
    return conditions


def _parse_paragraph(text: str) -> List[AcCondition]:
    """Parse as a single paragraph or split on sentence boundaries."""
    # If the text is short, treat as single condition
    if len(text.split()) < 30:
        condition = _create_condition(text, "AC-1")
        return [condition]
    
    # Split on periods followed by space (simple sentence detection)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    conditions = []
    for i, sent in enumerate(sentences, start=1):
        sent = sent.strip()
        if sent and len(sent.split()) > 5:  # Filter out very short fragments
            condition = _create_condition(sent, f"AC-{i}")
            conditions.append(condition)
    
    # If we got too many fragments, return single condition
    if len(conditions) > 20:
        condition = _create_condition(text, "AC-1")
        return [condition]
    
    return conditions if conditions else [_create_condition(text, "AC-1")]


def _create_condition(text: str, cond_id: str) -> AcCondition:
    """Create an AcCondition with detected features."""
    text = text.strip()
    
    # Detect validation rules (common keywords)
    validation_keywords = ["validate", "check", "verify", "assert", "must", "should", "required", "mandatory"]
    has_validation = any(kw in text.lower() for kw in validation_keywords)
    
    # Detect numeric boundaries (numbers, ranges, comparisons)
    has_numeric = bool(re.search(r'\d+\s*(?:to|-|through|and|,)\s*\d+|[<>≤≥]=?\s*\d+', text))
    
    # Extract input fields (common field name patterns)
    input_fields = _extract_field_names(text)
    
    # Determine scenario hints
    scenario_hints = _detect_scenario_hints(text)
    
    return AcCondition(
        id=cond_id,
        text=text,
        has_validation_rule=has_validation,
        has_numeric_boundary=has_numeric,
        input_fields=input_fields,
        scenario_hints=scenario_hints,
    )


def _extract_field_names(text: str) -> List[str]:
    """Extract potential input field names from text."""
    # Common field patterns
    patterns = [
        r"'([a-zA-Z_][a-zA-Z0-9_]*)' field",
        r'"([a-zA-Z_][a-zA-Z0-9_]*)" field',
        r'\b(username|password|email|phone|name|address|zip|date|amount|quantity)\b',
    ]
    
    fields = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        fields.update(m.lower() for m in matches)
    
    return sorted(list(fields))


def _detect_scenario_hints(text: str) -> List[str]:
    """Detect scenario types this condition suggests."""
    hints = ["positive"]  # Default
    
    # Negative scenarios
    negative_keywords = ["not", "invalid", "negative", "wrong", "error", "fail", "reject", "deny"]
    if any(kw in text.lower() for kw in negative_keywords):
        hints.append("negative")
    
    # Boundary scenarios
    boundary_keywords = ["limit", "maximum", "minimum", "boundary", "edge", "threshold"]
    if any(kw in text.lower() for kw in boundary_keywords):
        hints.append("boundary")
    
    # Edge cases
    edge_keywords = ["empty", "null", "special", "unicode", "extreme", "malformed"]
    if any(kw in text.lower() for kw in edge_keywords):
        hints.append("edge")
    
    return hints
