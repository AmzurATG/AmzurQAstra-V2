"""LangGraph state for orchestrated test runs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class CasePayload(TypedDict, total=False):
    test_case_id: int
    test_result_id: int
    title: str
    description: str
    preconditions: str
    steps: List[Dict[str, Any]]
    user_story_id: Optional[int]


class GroupRow(TypedDict, total=False):
    group_id: str
    title: str
    phase_order: List[str]
    case_ids: List[int]
    case_phases: Dict[str, str]
    merged_steps: Dict[str, Any]
    shared_login: bool
    status: str
    lane_id: Optional[int]


class CaseResult(TypedDict, total=False):
    test_case_id: int
    test_result_id: int
    title: str
    status: str
    duration_ms: int
    step_results: List[Dict[str, Any]]
    adapted_steps: List[Dict[str, Any]]
    original_steps: List[Dict[str, Any]]
    agent_logs: List[Dict[str, Any]]
    screenshot_path: Optional[str]
    ai_modified: Dict[str, Any]
    error: Optional[str]
    group_id: Optional[str]
    lane_id: Optional[int]


class OrchestrationState(TypedDict, total=False):
    run_id: int
    run_uuid: str
    project_id: int
    app_url: str
    username: Optional[str]
    password: Optional[str]
    use_google_signin: bool
    headless: bool
    cases: List[CasePayload]
    total_cases: int
    planner_count: int
    chunks: List[List[CasePayload]]
    partial_group_tables: List[List[GroupRow]]
    group_table: List[GroupRow]
    lane_count: int
    active_lanes: List[Dict[str, Any]]
    case_results: List[CaseResult]
    failed_case_ids: List[int]
    retry_results: List[CaseResult]
    completed_count: int
    status: str
    error: Optional[str]
    cancel_requested: bool
