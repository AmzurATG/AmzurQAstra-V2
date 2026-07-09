"""Evaluator fan-out: screenshots, log slicing, duration sharing."""
from __future__ import annotations

from types import SimpleNamespace

from features.functional.core.execution.evaluator_agent import (
    _slice_agent_logs_for_case,
    evaluate_group_results,
)
from features.functional.core.execution.execution_plan import (
    ExecutionGroup,
    MergedStep,
    PlannedCase,
)


def _group_two_cases() -> ExecutionGroup:
    return ExecutionGroup(
        group_id="G1",
        label="filters",
        session_type="shared",
        browser_lane=1,
        reset_url="https://example.com",
        ordered_cases=[
            PlannedCase(tc_id=10, order=1, reset_before=None, reason="shared"),
            PlannedCase(tc_id=11, order=2, reset_before=None, reason="shared"),
        ],
        merged_steps=[
            MergedStep(
                merged_step_number=1,
                action="navigate",
                description="Open filters",
                target=None,
                value=None,
                expected_result=None,
                satisfies=[
                    {"tc_id": 10, "step_number": 1},
                    {"tc_id": 11, "step_number": 1},
                ],
            ),
            MergedStep(
                merged_step_number=2,
                action="click",
                description="Clear filter (case 11 only)",
                target=None,
                value=None,
                expected_result=None,
                satisfies=[{"tc_id": 11, "step_number": 2}],
            ),
        ],
    )


def test_no_group_screenshot_fallback_when_case_has_no_shots():
    group = _group_two_cases()
    # Case 10 only maps to step 1, which has NO screenshot — must not steal group last shot.
    group_result = {
        "overall": "passed",
        "merged_step_results": [
            {
                "merged_step_number": 1,
                "status": "passed",
                "actual_result": "opened",
                "adaptation": None,
                "screenshot_path": None,
                "agent_actions": ["Opened filters"],
                "log_start_index": 0,
                "log_end_index": 2,
            },
            {
                "merged_step_number": 2,
                "status": "passed",
                "actual_result": "cleared",
                "adaptation": None,
                "screenshot_path": "/screenshots/clear.png",
                "agent_actions": ["Clicked Clear"],
                "log_start_index": 2,
                "log_end_index": 4,
            },
        ],
        "agent_logs": [
            {"description": "▶ Step 1/2", "screenshot_path": None},
            {"description": "   • Opened", "screenshot_path": None},
            {"description": "▶ Step 2/2", "screenshot_path": "/screenshots/clear.png"},
            {"description": "   • Clicked Clear", "screenshot_path": "/screenshots/clear.png"},
        ],
        "screenshots": ["/screenshots/clear.png"],
        "summary": "ok",
        "duration_ms": 372000,
        "error": None,
    }
    origin = {
        "G1:1": [
            {"tc_id": 10, "step_number": 1},
            {"tc_id": 11, "step_number": 1},
        ],
        "G1:2": [{"tc_id": 11, "step_number": 2}],
    }
    tc_data = {
        10: {"title": "A", "steps": [{"step_number": 1, "description": "Open"}]},
        11: {
            "title": "B",
            "steps": [
                {"step_number": 1, "description": "Open"},
                {"step_number": 2, "description": "Clear"},
            ],
        },
    }
    out = evaluate_group_results(
        group=group,
        group_result=group_result,
        step_origin_map=origin,
        tc_data=tc_data,
    )
    assert out[10]["screenshot_path"] is None
    assert out[10]["agent_screenshot_count"] == 0
    assert out[11]["screenshot_path"] == "/screenshots/clear.png"
    # Count = steps with a shot (step 2 only), not distinct files
    assert out[11]["agent_screenshot_count"] == 1
    # Shared duration split across 2 cases
    assert out[10]["duration_ms"] == 186000
    assert out[11]["duration_ms"] == 186000
    assert out[10]["group_duration_ms"] == 372000
    assert out[10]["shared_session"] is True
    # Case 10 logs must not include Clear step
    descs = " ".join(e.get("description", "") for e in out[10]["agent_logs"])
    assert "Clear" not in descs
    assert "Step 1" in descs or "Opened" in descs


def test_screenshot_count_matches_steps_with_shared_file():
    """Same PNG reused on 3 steps still counts as 3 in the UI badge."""
    group = ExecutionGroup(
        group_id="G2",
        label="one",
        session_type="shared",
        browser_lane=1,
        reset_url="https://example.com",
        ordered_cases=[PlannedCase(tc_id=1, order=1, reset_before=None, reason="x")],
        merged_steps=[
            MergedStep(
                merged_step_number=i,
                action="custom",
                description=f"s{i}",
                satisfies=[{"tc_id": 1, "step_number": i}],
            )
            for i in (1, 2, 3)
        ],
    )
    shared = "/screenshots/same.png"
    group_result = {
        "overall": "passed",
        "merged_step_results": [
            {
                "merged_step_number": i,
                "status": "passed",
                "actual_result": "ok",
                "screenshot_path": shared,
                "agent_actions": [],
                "log_start_index": 0,
                "log_end_index": 0,
            }
            for i in (1, 2, 3)
        ],
        "agent_logs": [],
        "screenshots": [shared],
        "summary": "",
        "duration_ms": 3000,
        "error": None,
    }
    origin = {f"G2:{i}": [{"tc_id": 1, "step_number": i}] for i in (1, 2, 3)}
    tc_data = {
        1: {
            "title": "T",
            "steps": [{"step_number": i, "description": f"s{i}"} for i in (1, 2, 3)],
        }
    }
    out = evaluate_group_results(
        group=group, group_result=group_result, step_origin_map=origin, tc_data=tc_data
    )
    assert out[1]["agent_screenshot_count"] == 3
    assert len(out[1]["screenshots"]) == 1  # distinct files still 1


def test_slice_agent_logs_by_index_ranges():
    logs = [
        {"description": "▶ Step 1/2"},
        {"description": "   • a"},
        {"description": "▶ Step 2/2"},
        {"description": "   • b"},
    ]
    ms = [
        {"merged_step_number": 1, "log_start_index": 0, "log_end_index": 2},
        {"merged_step_number": 2, "log_start_index": 2, "log_end_index": 4},
    ]
    sliced = _slice_agent_logs_for_case(logs, ms, {2})
    assert len(sliced) == 2
    assert "Step 2" in sliced[0]["description"]
