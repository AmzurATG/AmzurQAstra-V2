"""
Coverage Matrix Builder — constructs a coverage matrix from AC conditions.

A CoverageMatrix represents the test scenarios derived from acceptance criteria
conditions, mapped to generate test cases. It tracks combinations of conditions
and the expected scenarios to test.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class CoverageMatrix:
    """
    Represents a coverage matrix built from AC conditions.
    
    The matrix encodes:
    - Base conditions from AC decomposition
    - Derived scenario combinations
    - Profile-driven coverage expectations
    """
    
    def __init__(
        self,
        story_id: Optional[int] = None,
        story_title: str = "",
        profile: str = "standard",
        conditions: Optional[List[Dict[str, Any]]] = None,
        matrix_data: Optional[List[Dict[str, Any]]] = None,
        inventory: Optional[Dict[str, Any]] = None,
    ):
        self.story_id = story_id
        self.story_title = story_title
        self.profile = profile
        self.conditions = conditions or []
        self.matrix_data = matrix_data or []
        self.inventory = inventory or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert matrix to dictionary representation."""
        return {
            "story_id": self.story_id,
            "story_title": self.story_title,
            "profile": self.profile,
            "conditions": self.conditions,
            "matrix_data": self.matrix_data,
            "inventory": self.inventory,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CoverageMatrix:
        """Create matrix from dictionary representation."""
        return cls(
            story_id=data.get("story_id"),
            story_title=data.get("story_title", ""),
            profile=data.get("profile", "standard"),
            conditions=data.get("conditions", []),
            matrix_data=data.get("matrix_data", []),
            inventory=data.get("inventory", {}),
        )


def build_matrix(
    conditions: List[Dict[str, Any]],
    story_title: str,
    profile: str = "standard",
    inventory: Optional[Dict[str, Any]] = None,
    story_id: Optional[int] = None,
) -> CoverageMatrix:
    """
    Build a coverage matrix from AC conditions.
    
    Args:
        conditions: List of AC conditions from decomposition
        story_title: Title of the user story
        profile: Generation profile (light, standard, comprehensive)
        inventory: Optional UI inventory for the story
        story_id: Optional story ID
    
    Returns:
        CoverageMatrix instance ready for test case generation
    """
    # Build matrix data based on conditions and profile
    matrix_data = []
    
    # Generate scenarios based on profile
    scenario_count = _get_scenario_count_for_profile(profile)
    
    # Create matrix rows from conditions
    for i, condition in enumerate(conditions):
        for j in range(scenario_count):
            row = {
                "index": len(matrix_data),
                "condition_id": i,
                "condition": condition,
                "scenario_index": j,
                "scenario_type": _get_scenario_type(j, scenario_count),
            }
            matrix_data.append(row)
    
    matrix = CoverageMatrix(
        story_id=story_id,
        story_title=story_title,
        profile=profile,
        conditions=conditions,
        matrix_data=matrix_data,
        inventory=inventory,
    )
    
    return matrix


def _get_scenario_count_for_profile(profile: str) -> int:
    """Get the number of scenarios per condition for a given profile."""
    profile_map = {
        "light": 5,
        "standard": 10,
        "comprehensive": 20,
    }
    return profile_map.get(profile, 10)


def _get_scenario_type(index: int, total: int) -> str:
    """
    Determine scenario type based on index and total count.
    
    Returns a mix of positive, negative, boundary, and edge scenarios.
    """
    ratio = index / max(total, 1)
    
    if ratio < 0.5:
        return "positive"
    elif ratio < 0.75:
        return "negative"
    elif ratio < 0.9:
        return "boundary"
    else:
        return "edge"
