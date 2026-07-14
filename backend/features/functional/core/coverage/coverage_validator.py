"""
Coverage validator — compares generated test-case specs against a CoverageMatrix.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from features.functional.core.coverage.matrix_builder import CoverageMatrix


@dataclass
class CoverageGap:
    """Missing coverage for one (ac_ref, scenario_type) pair."""

    ac_ref: str
    scenario_type: str
    required_count: int
    actual_count: int

    @property
    def missing_count(self) -> int:
        return max(0, self.required_count - self.actual_count)


@dataclass
class CoverageReport:
    """Result of validating generated specs against the matrix."""

    coverage_percent: float
    gaps: List[CoverageGap] = field(default_factory=list)
    total_required: int = 0
    total_covered: int = 0

    @property
    def has_gaps(self) -> bool:
        return any(g.missing_count > 0 for g in self.gaps)


def _key(ac_ref: str, scenario_type: str) -> Tuple[str, str]:
    return ((ac_ref or "").strip(), (scenario_type or "").strip().lower())


def validate(matrix: CoverageMatrix, specs: Sequence[Dict[str, Any]]) -> CoverageReport:
    """
    Ensure each matrix row has at least one matching generated spec
    (matched on ac_ref + scenario_type).
    """
    required: Dict[Tuple[str, str], int] = defaultdict(int)
    for row in matrix.rows:
        required[_key(row.ac_ref, row.scenario_type)] += 1

    actual: Dict[Tuple[str, str], int] = defaultdict(int)
    for spec in specs or []:
        actual[_key(str(spec.get("ac_ref") or ""), str(spec.get("scenario_type") or ""))] += 1

    gaps: List[CoverageGap] = []
    covered = 0
    total = 0
    for pair, req_count in required.items():
        act_count = actual.get(pair, 0)
        total += req_count
        covered += min(req_count, act_count)
        if act_count < req_count:
            gaps.append(
                CoverageGap(
                    ac_ref=pair[0],
                    scenario_type=pair[1],
                    required_count=req_count,
                    actual_count=act_count,
                )
            )

    percent = round((covered / total) * 100.0, 1) if total else 100.0
    return CoverageReport(
        coverage_percent=percent,
        gaps=gaps,
        total_required=total,
        total_covered=covered,
    )


# Public alias used by BulkGenerationService
validate_coverage = validate
