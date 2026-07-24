"""LangGraph multi-agent orchestration for run-all test execution."""

from typing import Any

__all__ = ["build_orchestration_graph", "OrchestratedRunService"]


def __getattr__(name: str) -> Any:
    if name == "build_orchestration_graph":
        from features.functional.orchestration.graph import build_orchestration_graph

        return build_orchestration_graph
    if name == "OrchestratedRunService":
        from features.functional.orchestration.orchestrated_run_service import (
            OrchestratedRunService,
        )

        return OrchestratedRunService
    raise AttributeError(name)
