"""Unit tests for segmented-run STEP_VERDICT parsing / action synthesis."""
from __future__ import annotations

from features.functional.core.execution.shared_session_runner import (
    _action_lines_from_logs,
    _parse_segment_verdict,
    _synthesize_actual_from_actions,
)


class _Hist:
    def __init__(self, ok=None, final=""):
        self._ok = ok
        self._final = final

    def is_successful(self):
        return self._ok

    def final_result(self):
        return self._final


def test_parse_explicit_step_verdict_pass():
    status, actual, adapt, src = _parse_segment_verdict(
        "STEP_VERDICT: PASS — League size set to 10 | ADAPTED: used Size dropdown",
        None,
    )
    assert status == "passed"
    assert "League size set to 10" in actual
    assert adapt and "Size dropdown" in adapt
    assert src == "explicit"


def test_parse_explicit_step_verdict_fail():
    status, actual, adapt, src = _parse_segment_verdict(
        "STEP_VERDICT: FAIL — Create League button not found",
        None,
    )
    assert status == "failed"
    assert "not found" in actual.lower()
    assert adapt is None
    assert src == "explicit"


def test_fallback_uses_action_trail_not_placeholder():
    actions = ["Clicked 'Leagues'", "Clicked 'Create League'", "Entered text into 'Size'"]
    status, actual, _, src = _parse_segment_verdict(
        "",
        _Hist(ok=True),
        action_descriptions=actions,
        expected_result="League size is 10",
    )
    assert status == "passed"
    assert "Step completed (no explicit verdict" not in actual
    assert "Observed actions" in actual
    assert "Create League" in actual
    assert "Expected:" in actual
    assert src == "inferred_success"


def test_fallback_no_evidence_is_error():
    status, actual, _, src = _parse_segment_verdict("", _Hist(ok=None), action_descriptions=[])
    assert status == "error"
    assert "No STEP_VERDICT" in actual
    assert "Step completed (no explicit verdict" not in actual
    assert src == "error"


def test_failure_keywords_mark_failed():
    status, actual, _, src = _parse_segment_verdict(
        "Could not click the Create League button",
        _Hist(ok=None),
        action_descriptions=["Clicked 'Leagues'"],
    )
    assert status == "failed"
    assert "Could not click" in actual
    assert src == "inferred_failure"


def test_action_lines_from_logs_strips_headers_and_bullets():
    logs = [
        {"description": "▶ Step 1/2 [PASSED]: Login"},
        {"description": "   • Clicked 'Sign in'"},
        {"description": "• Entered text into 'Email'"},
    ]
    assert _action_lines_from_logs(logs) == [
        "Clicked 'Sign in'",
        "Entered text into 'Email'",
    ]


def test_synthesize_includes_expected():
    text = _synthesize_actual_from_actions(
        ["Clicked 'Save'"],
        expected_result="League saved",
        note="Inferred PASS.",
    )
    assert "Inferred PASS" in text
    assert "Expected: League saved" in text
    assert "Clicked 'Save'" in text


def test_inferred_actions_source_when_no_success_flag():
    status, actual, _, src = _parse_segment_verdict(
        "",
        _Hist(ok=None),
        action_descriptions=["Clicked 'Save'"],
    )
    assert status == "passed"
    assert src == "inferred_actions"
    assert "Observed actions" in actual
