"""Unit tests for accuracy-first core (gates, grouping, final status)."""
from __future__ import annotations

import pytest

from features.functional.core.accuracy.final_status import resolve_final_status
from features.functional.core.accuracy.gates import ScreenshotGate, VerdictGate
from features.functional.core.accuracy.types import VerdictSource
from features.functional.core.grouping.setup_step_merger import (
    is_setup_step,
    leading_setup_count,
    merge_step_results_with_skipped_setup,
    prepare_steps_for_shared_session,
)
from features.functional.core.grouping.side_effect_classifier import (
    SideEffectClass,
    classify_side_effect,
)
from features.functional.core.grouping.subgroup_splitter import split_group, split_group_table


class TestScreenshotGate:
    def test_ok_when_shots_present(self):
        assert (
            ScreenshotGate.evaluate(
                capture_screenshots=True,
                screenshots=["/screenshots/a.png"],
                overall="passed",
            )
            is None
        )

    def test_fails_without_shots(self):
        fail = ScreenshotGate.evaluate(
            capture_screenshots=True,
            screenshots=[],
            agent_logs=[],
            overall="failed",
        )
        assert fail is not None
        assert fail["error_kind"] == "missing_screenshots"
        assert fail["infra_error"] is True

    def test_skips_when_capture_disabled(self):
        assert (
            ScreenshotGate.evaluate(
                capture_screenshots=False,
                screenshots=[],
                overall="passed",
            )
            is None
        )


class TestVerdictGate:
    def test_parsed_not_inconclusive(self):
        v = VerdictGate.tag_verdict(
            {"overall": "passed", "steps": []},
            VerdictSource.PARSED,
        )
        assert v["verdict_source"] == "parsed"
        assert not v.get("inconclusive")

    def test_fallback_marked_inconclusive(self):
        v = VerdictGate.tag_verdict(
            {"overall": "failed", "steps": [{"status": "failed"}]},
            VerdictSource.FALLBACK,
        )
        assert v["verdict_source"] == "fallback"
        assert v.get("inconclusive") is True

    def test_exhausted_payload(self):
        p = VerdictGate.exhausted_payload(
            screenshots=["x"],
            agent_logs=[],
            steps_total=3,
            duration_ms=10,
            original_steps=[
                {"step_number": 1, "description": "a"},
                {"step_number": 2, "description": "b"},
                {"step_number": 3, "description": "c"},
            ],
        )
        assert p["error"] == "missing_verdict_json"
        assert len(p["step_results"]) == 3
        assert p["step_results"][0].get("infra_blocked") is True
        assert p["infra_error"] is True
        assert p["user_message"]


class TestFinalStatus:
    def test_agree(self):
        d = resolve_final_status(
            executor_status="failed",
            ui_verdict="failed",
            ui_confidence=0.9,
            has_screenshots=True,
        )
        assert d["status"] == "failed"
        assert d["ui_override"] is False

    def test_prefer_ui_high_confidence(self):
        d = resolve_final_status(
            executor_status="failed",
            ui_verdict="passed",
            ui_confidence=0.9,
            ui_payload={"ui_verdict": "passed"},
            has_screenshots=True,
        )
        assert d["status"] == "passed"
        assert d["ui_override"] is True
        assert d["executor_status"] == "failed"

    def test_conflict_low_confidence(self):
        d = resolve_final_status(
            executor_status="passed",
            ui_verdict="failed",
            ui_confidence=0.4,
            has_screenshots=True,
        )
        assert d["status"] == "error"
        assert d["error_kind"] == "verdict_conflict"


class TestSetupMerger:
    def test_detect_login_setup(self):
        assert is_setup_step(
            {"action": "custom", "description": "Login as Support Admin"}
        )
        assert is_setup_step(
            {"action": "type", "description": "Enter the URL in a browser and launch"}
        )
        assert not is_setup_step(
            {"action": "custom", "description": "Click Force Password Reset"}
        )

    def test_strip_leading_setup(self):
        steps = [
            {"step_number": 1, "action": "type", "description": "Enter the URL and launch"},
            {"step_number": 2, "action": "custom", "description": "Login as Admin"},
            {"step_number": 3, "action": "custom", "description": "Verify Unlock popup"},
        ]
        assert leading_setup_count(steps) == 2
        run, skipped, ctx = prepare_steps_for_shared_session(steps, session_warm=True)
        assert ctx == "already_authenticated"
        assert len(skipped) == 2
        assert len(run) == 1
        assert run[0]["step_number"] == 3
        assert "Already signed in" in skipped[0]["actual_result"]
        assert skipped[0]["status"] == "passed"
        assert skipped[0]["shared_setup"] is True

    def test_merge_results_keeps_skipped(self):
        original = [
            {"step_number": 1, "description": "Login"},
            {"step_number": 2, "description": "Assert"},
        ]
        skipped = [
            {
                "step_number": 1,
                "description": "Login",
                "status": "passed",
                "actual_result": "Already signed in — login completed earlier in this session.",
                "shared_setup": True,
                "screenshot_path": "/screenshots/login.png",
            }
        ]
        run_res = [
            {"step_number": 2, "status": "passed", "actual_result": "ok"},
        ]
        merged = merge_step_results_with_skipped_setup(original, skipped, run_res)
        assert merged[0]["status"] == "passed"
        assert merged[0]["shared_setup"] is True
        assert merged[0]["screenshot_path"] == "/screenshots/login.png"
        assert merged[1]["status"] == "passed"


class TestSubgroupSplitter:
    def _cases(self, n: int, *, title_prefix: str = "Verify filter"):
        return [
            {
                "test_case_id": i + 1,
                "title": f"{title_prefix} {i+1}",
                "description": "",
                "steps": [{"step_number": 1, "description": "check column"}],
            }
            for i in range(n)
        ]

    def test_preserves_all_case_ids(self):
        cases = self._cases(20, title_prefix="Verify Unlock Account")
        group = {
            "group_id": "G9",
            "title": "Unlock Account",
            "case_ids": [c["test_case_id"] for c in cases],
            "case_phases": {str(c["test_case_id"]): "authed" for c in cases},
            "phase_order": ["authed"],
            "merged_steps": {"login": {"run_once": True}},
            "shared_login": True,
            "status": "pending",
        }
        subs = split_group(group, cases)
        ids = []
        for s in subs:
            ids.extend(s["case_ids"])
            assert s["parent_group_id"] == "G9"
            assert s["title"].startswith("Unlock Account ·")
            assert len(s["case_ids"]) <= 10
        assert sorted(ids) == list(range(1, 21))

    def test_small_group_unchanged_size(self):
        cases = self._cases(3)
        group = {
            "group_id": "G1",
            "title": "Filters",
            "case_ids": [1, 2, 3],
            "case_phases": {"1": "authed", "2": "authed", "3": "authed"},
            "phase_order": ["authed"],
            "merged_steps": {},
            "shared_login": True,
            "status": "pending",
        }
        subs = split_group(group, cases)
        assert len(subs) == 1
        assert subs[0]["case_ids"] == [1, 2, 3]

    def test_table_no_duplicate_cases(self):
        cases = self._cases(10, title_prefix="Delete user")
        groups = [
            {
                "group_id": "Ga",
                "title": "Delete",
                "case_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "case_phases": {},
                "phase_order": ["authed"],
                "merged_steps": {},
                "shared_login": True,
                "status": "pending",
            }
        ]
        out = split_group_table(groups, cases)
        flat = [c for g in out for c in g["case_ids"]]
        assert len(flat) == len(set(flat)) == 10


class TestSideEffect:
    def test_destructive(self):
        assert (
            classify_side_effect({"title": "Verify delete admin account", "steps": []})
            == SideEffectClass.DESTRUCTIVE
        )

    def test_mutating(self):
        assert (
            classify_side_effect({"title": "Verify Force Password Reset", "steps": []})
            == SideEffectClass.MUTATING
        )


class TestStepDisplayCounts:
    def test_includes_shared_setup_in_totals(self):
        from features.functional.core.grouping.setup_step_merger import compute_step_display_counts

        steps = [
            {"status": "passed", "actual_result": "Already signed in — login completed earlier in this session.", "shared_setup": True},
            {"status": "passed", "actual_result": "ok"},
            {"status": "failed", "actual_result": "no"},
        ]
        c = compute_step_display_counts(steps)
        assert c["setup_skipped_count"] == 1
        assert c["steps_total"] == 3
        assert c["steps_passed"] == 2
        assert c["steps_failed"] == 1


class TestScreenshotAgent:
    def test_curates_down_from_spam(self):
        from features.functional.core.screenshots import ScreenshotAgent

        logs = [
            {"agent_step": i, "description": f"s{i}", "screenshot_path": f"/screenshots/{i}.png"}
            for i in range(40)
        ]
        out = ScreenshotAgent.curate(logs, overall="failed")
        assert out["evidence_screenshot_count"] <= 8
        assert out["raw_screenshot_count"] == 40
        evidenced = [e for e in out["agent_logs"] if e.get("evidence") is True]
        assert len(evidenced) == out["evidence_screenshot_count"]
        # Non-evidence paths cleared for UI
        assert sum(1 for e in out["agent_logs"] if e.get("screenshot_path")) == out["evidence_screenshot_count"]

    def test_pass_cap_smaller(self):
        from features.functional.core.screenshots import ScreenshotAgent

        logs = [
            {"agent_step": i, "description": f"s{i}", "screenshot_path": f"/screenshots/{i}.png"}
            for i in range(20)
        ]
        out = ScreenshotAgent.curate(logs, overall="passed")
        assert out["evidence_screenshot_count"] <= 6


class TestUiConsistencyRules:
    def test_passed_zero_steps_desync(self):
        from features.functional.core.ui_consistency.rules import detect_desync

        evt = detect_desync(
            {
                "status": "passed",
                "steps_passed": 0,
                "steps_total": 3,
                "agent_screenshot_count": 2,
                "test_case_id": 1,
            }
        )
        assert evt is not None
        assert "passed_with_zero_verified_steps" in evt["reasons"]

    def test_clean_entry(self):
        from features.functional.core.ui_consistency.rules import detect_desync

        assert (
            detect_desync(
                {
                    "status": "passed",
                    "steps_passed": 2,
                    "steps_total": 2,
                    "agent_screenshot_count": 1,
                }
            )
            is None
        )


class TestWatchdogPolicy:
    def test_slow_case_reassign(self):
        from features.functional.core.supervisor.watchdog import LaneWatchdog

        wd = LaneWatchdog()
        wd.slow_case_ms  # access
        # Override via monkeypatch of settings is heavy — use elapsed by faking start
        wd.start_case(test_case_id=1, lane_id=2)
        w = wd._active[1]
        w.started_at -= (wd.slow_case_ms / 1000.0) + 1
        d = wd.evaluate(1)
        assert d.action == "reassign"
        assert "slow_case" in d.reason

    def test_max_reassigns(self):
        from features.functional.core.supervisor.watchdog import LaneWatchdog

        wd = LaneWatchdog()
        wd.start_case(test_case_id=5, lane_id=1, reassign_count=2)
        assert wd.can_reassign(5) is False


class TestMemoryStore:
    def test_roundtrip(self, tmp_path, monkeypatch):
        from features.functional.core import memory as mem_pkg
        from features.functional.core.memory import store as store_mod

        monkeypatch.setattr(store_mod, "_memory_root", lambda: tmp_path)
        store_mod.append_event(99, {"type": "recon_failure", "error": "x"}, hint="check login")
        data = store_mod.load_memory(99)
        assert data["events"][-1]["type"] == "recon_failure"
        assert "check login" in data["hints"]


class TestLaneNoScaleUp:
    def test_scale_up_disabled(self, monkeypatch):
        import config
        from features.functional.orchestration import lane_pool as lp

        monkeypatch.setattr(config.settings, "ORCHESTRATION_LANE_SCALE_UP", False)
        monkeypatch.setattr(config.settings, "ORCHESTRATION_LANE_COUNT", 6)
        monkeypatch.setattr(config.settings, "ORCHESTRATION_MAX_LANE_COUNT", 12)
        monkeypatch.setattr(config.settings, "ORCHESTRATION_MIN_FREE_RAM_MB", 0)
        monkeypatch.setattr(config.settings, "ORCHESTRATION_PER_LANE_RAM_MB", 1)
        monkeypatch.setattr(lp, "_free_ram_mb", lambda: 100_000.0)
        assert lp.effective_lane_count(6) == 6


class TestGraphNodes:
    def test_node_list_includes_supervisor_stack(self):
        from features.functional.orchestration.graph import build_orchestration_graph

        g = build_orchestration_graph(lambda: None)
        names = set(g.nodes.keys()) if hasattr(g, "nodes") else set()
        # langgraph StateGraph stores nodes differently across versions
        if not names and hasattr(g, "_nodes"):
            names = set(g._nodes.keys())
        expected = {
            "supervisor",
            "recon",
            "orchestrator",
            "planner",
            "merge",
            "subgroup",
            "execute",
            "evidence",
            "vision_retry",
            "ui_validate",
            "report",
        }
        assert expected.issubset(names)


class TestStatusNarrator:
    def test_infra_stubs_not_empty(self):
        from features.functional.core.status_narrator import infra_step_stubs, narrate_case_result

        steps = [
            {"step_number": 1, "description": "Login"},
            {"step_number": 2, "description": "Click Unlock"},
        ]
        stubs = infra_step_stubs(steps, error_kind="rate")
        assert len(stubs) == 2
        assert stubs[0]["infra_blocked"] is True
        assert "rate" in stubs[0]["actual_result"].lower() or "busy" in stubs[0]["actual_result"].lower()

        narrated = narrate_case_result(
            {
                "overall": "error",
                "infra_error": True,
                "error_kind": "rate",
                "step_results": [],
            },
            steps,
        )
        assert len(narrated["step_results"]) == 2
        assert narrated["overall"] == "error"
        assert narrated["user_message"]


class TestCircuitDegraded:
    def test_degrade_before_open(self):
        from features.functional.core.browser.llm_gate import (
            CircuitState,
            LLMErrorKind,
            LLMGate,
        )
        import asyncio

        gate = LLMGate()
        gate._breaker.degrade_threshold = 2
        gate._breaker.failure_threshold = 10

        async def _run():
            await gate._breaker.record_failure(LLMErrorKind.RATE, model="gemini/x")
            await gate._breaker.record_failure(LLMErrorKind.RATE, model="gemini/x")
            assert gate._breaker.state == CircuitState.DEGRADED
            assert gate.model_available("gpt-4o") is True
            assert gate.model_available("gemini/x") is False

        asyncio.run(_run())

    def test_classify_no_deployments(self):
        from features.functional.core.browser.llm_gate import LLMErrorKind, classify_llm_error

        exc = Exception(
            "No deployments available for selected model, Try again in 30 seconds. "
            "cooldown_list=['abc']"
        )
        assert classify_llm_error(exc) == LLMErrorKind.RATE


class TestRunGovernor:
    def test_open_waits(self):
        from features.functional.core.browser.llm_gate import CircuitState, get_gate
        from features.functional.core.run_governor import RunGovernor

        gate = get_gate()
        gate.reset()
        gate._breaker.state = CircuitState.OPEN
        gate._breaker.open_until = gate._breaker.open_until or (__import__("time").monotonic() + 30)
        # force open_until in future
        import time

        gate._breaker.open_until = time.monotonic() + 30
        d = RunGovernor().evaluate()
        assert d.action in ("wait", "pause")
        assert d.banner is not None
        gate.reset()

