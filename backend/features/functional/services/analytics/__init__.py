"""Functional analytics service package."""

from features.functional.services.analytics.analytics_service import (
    WINDOW_DAYS,
    build_functional_project_analytics,
)

__all__ = ["WINDOW_DAYS", "build_functional_project_analytics"]
