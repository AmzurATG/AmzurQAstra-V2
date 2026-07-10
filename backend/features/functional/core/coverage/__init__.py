"""
Coverage analysis module for test case generation.

Provides coverage matrix construction and validation for the bulk generation
pipeline. Tracks which test scenarios are covered and identifies gaps.
"""
from features.functional.core.coverage.ac_parser import (
    AcCondition,
    parse as parse_ac,
)
from features.functional.core.coverage.coverage_validator import (
    CoverageReport,
    validate_coverage,
)
from features.functional.core.coverage.matrix_builder import (
    CoverageMatrix,
    build_matrix,
)

__all__ = [
    "AcCondition",
    "CoverageMatrix",
    "CoverageReport",
    "build_matrix",
    "parse_ac",
    "validate_coverage",
]
