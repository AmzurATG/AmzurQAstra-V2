"""Analytics source enum; v1 only functional test runs are implemented."""

from __future__ import annotations

from enum import Enum


class AnalyticsSource(str, Enum):
    FUNCTIONAL = "functional"
    INTEGRITY = "integrity"
    PERFORMANCE = "performance"
    SECURITY = "security"


def parse_source(value: str) -> AnalyticsSource:
    try:
        return AnalyticsSource(value.lower().strip())
    except ValueError as exc:
        raise ValueError(f"Unknown analytics source: {value!r}") from exc
