"""Build and compile the LangGraph orchestration workflow."""
from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, StateGraph

from features.functional.orchestration.checkpointer import get_checkpointer
from features.functional.orchestration.nodes.evidence import evidence_node
from features.functional.orchestration.nodes.executor import execute_node
from features.functional.orchestration.nodes.merge import merge_node
from features.functional.orchestration.nodes.orchestrator import orchestrator_node
from features.functional.orchestration.nodes.planner import planner_node
from features.functional.orchestration.nodes.recon import recon_node
from features.functional.orchestration.nodes.report import report_node
from features.functional.orchestration.nodes.subgroup import subgroup_node
from features.functional.orchestration.nodes.supervisor import supervisor_node
from features.functional.orchestration.nodes.ui_validate import ui_validate_node
from features.functional.orchestration.nodes.vision_retry import vision_retry_node
from features.functional.orchestration.state import OrchestrationState


def _route_after_evidence(state: OrchestrationState) -> str:
    if state.get("failed_case_ids"):
        return "vision_retry"
    return "ui_validate"


def _route_after_supervisor(state: OrchestrationState) -> str:
    if state.get("status") == "error" or (state.get("supervisor") or {}).get("abort"):
        return "report"
    return "recon"


def _route_after_recon(state: OrchestrationState) -> str:
    if state.get("status") == "error":
        return "report"
    return "orchestrator"


def build_orchestration_graph(db_session_factory: Callable[..., Any]) -> StateGraph:
    async def _report_wrapper(state: OrchestrationState) -> dict:
        return await report_node(state, db_session_factory=db_session_factory)

    graph = StateGraph(OrchestrationState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("recon", recon_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("planner", planner_node)
    graph.add_node("merge", merge_node)
    graph.add_node("subgroup", subgroup_node)
    graph.add_node("execute", execute_node)
    graph.add_node("evidence", evidence_node)
    graph.add_node("vision_retry", vision_retry_node)
    graph.add_node("ui_validate", ui_validate_node)
    graph.add_node("report", _report_wrapper)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {"recon": "recon", "report": "report"},
    )
    graph.add_conditional_edges(
        "recon",
        _route_after_recon,
        {"orchestrator": "orchestrator", "report": "report"},
    )
    graph.add_edge("orchestrator", "planner")
    graph.add_edge("planner", "merge")
    graph.add_edge("merge", "subgroup")
    graph.add_edge("subgroup", "execute")
    graph.add_edge("execute", "evidence")
    graph.add_conditional_edges(
        "evidence",
        _route_after_evidence,
        {"vision_retry": "vision_retry", "ui_validate": "ui_validate"},
    )
    graph.add_edge("vision_retry", "ui_validate")
    graph.add_edge("ui_validate", "report")
    graph.add_edge("report", END)
    return graph


async def compile_orchestration_graph(db_session_factory: Callable[..., Any]):
    builder = build_orchestration_graph(db_session_factory)
    checkpointer = await get_checkpointer()
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()
