"""
Coverage package — AC parse → matrix build → coverage validate.

Public façade used by BulkGenerationService and related design services.
"""
from features.functional.core.coverage.ac_parser import AcCondition, parse
from features.functional.core.coverage.coverage_validator import (
    CoverageGap,
    CoverageReport,
    validate,
    validate_coverage,
)
from features.functional.core.coverage.matrix_builder import (
    CoverageMatrix,
    MatrixRow,
    build,
    build_matrix,
)

__all__ = [
    "AcCondition",
    "parse",
    "CoverageMatrix",
    "MatrixRow",
    "build",
    "build_matrix",
    "CoverageGap",
    "CoverageReport",
    "validate",
    "validate_coverage",
]
