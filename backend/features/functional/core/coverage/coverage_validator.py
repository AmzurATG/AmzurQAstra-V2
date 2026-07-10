"""
Coverage Validator — validates test case specs against coverage matrix.

Analyzes whether test case specs adequately cover the scenarios defined in
the coverage matrix and identifies gaps for gap-filling LLM requests.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class CoverageReport:
    """
    Report of coverage analysis from a CoverageMatrix and test case specs.
    
    Tracks coverage percentage, identified gaps, and recommendations for
    additional test cases to fill those gaps.
    """
    
    def __init__(
        self,
        matrix_scenarios: int = 0,
        covered_scenarios: int = 0,
        coverage_percent: float = 0.0,
        has_gaps: bool = False,
        gaps: Optional[List[Dict[str, Any]]] = None,
        gap_recommendations: Optional[List[Dict[str, Any]]] = None,
    ):
        self.matrix_scenarios = matrix_scenarios
        self.covered_scenarios = covered_scenarios
        self.coverage_percent = coverage_percent
        self.has_gaps = has_gaps
        self.gaps = gaps or []
        self.gap_recommendations = gap_recommendations or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary representation."""
        return {
            "matrix_scenarios": self.matrix_scenarios,
            "covered_scenarios": self.covered_scenarios,
            "coverage_percent": self.coverage_percent,
            "has_gaps": self.has_gaps,
            "gaps": self.gaps,
            "gap_recommendations": self.gap_recommendations,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CoverageReport:
        """Create report from dictionary representation."""
        return cls(
            matrix_scenarios=data.get("matrix_scenarios", 0),
            covered_scenarios=data.get("covered_scenarios", 0),
            coverage_percent=data.get("coverage_percent", 0.0),
            has_gaps=data.get("has_gaps", False),
            gaps=data.get("gaps", []),
            gap_recommendations=data.get("gap_recommendations", []),
        )


def validate_coverage(
    matrix: Any,  # CoverageMatrix
    specs: List[Dict[str, Any]],
    coverage_threshold: float = 0.8,
) -> CoverageReport:
    """
    Validate test case specs against coverage matrix.
    
    Analyzes how well the provided specs cover the scenarios in the matrix.
    Identifies gaps when coverage falls below the threshold.
    
    Args:
        matrix: CoverageMatrix instance from build_matrix()
        specs: List of test case spec dictionaries from LLM generation
        coverage_threshold: Minimum coverage percentage (0.0-1.0) to avoid gaps
    
    Returns:
        CoverageReport with coverage metrics and gap analysis
    """
    if not matrix.matrix_data:
        return CoverageReport(
            matrix_scenarios=0,
            covered_scenarios=0,
            coverage_percent=100.0,
            has_gaps=False,
        )
    
    matrix_scenarios = len(matrix.matrix_data)
    
    # Count specs that map to matrix scenarios
    # Each spec should ideally map to one or more matrix scenarios
    covered_scenarios = min(len(specs), matrix_scenarios)
    
    # Calculate coverage percentage
    coverage_percent = (covered_scenarios / matrix_scenarios * 100) if matrix_scenarios > 0 else 100.0
    
    # Determine if there are gaps
    has_gaps = (coverage_percent / 100.0) < coverage_threshold
    
    # Build gap list if needed
    gaps = []
    if has_gaps and matrix_scenarios > covered_scenarios:
        uncovered_count = matrix_scenarios - covered_scenarios
        for i in range(uncovered_count):
            gap_idx = covered_scenarios + i
            if gap_idx < len(matrix.matrix_data):
                gap_row = matrix.matrix_data[gap_idx]
                gaps.append({
                    "index": gap_idx,
                    "condition": gap_row.get("condition", {}),
                    "scenario_type": gap_row.get("scenario_type", "unknown"),
                    "reason": "Underrepresented in test specs",
                })
    
    # Create recommendations for gap filling
    gap_recommendations = []
    if has_gaps:
        scenario_type_counts: Dict[str, int] = {}
        for gap in gaps:
            stype = gap.get("scenario_type", "unknown")
            scenario_type_counts[stype] = scenario_type_counts.get(stype, 0) + 1
        
        for stype, count in scenario_type_counts.items():
            gap_recommendations.append({
                "scenario_type": stype,
                "count": count,
                "reason": f"Need {count} more {stype} scenario(s) for full coverage",
            })
    
    return CoverageReport(
        matrix_scenarios=matrix_scenarios,
        covered_scenarios=covered_scenarios,
        coverage_percent=coverage_percent,
        has_gaps=has_gaps,
        gaps=gaps,
        gap_recommendations=gap_recommendations,
    )
