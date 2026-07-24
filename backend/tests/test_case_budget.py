"""Unit tests for adaptive case budgets and duration formatting."""
from __future__ import annotations


class TestFormatDurationMs:
    def test_none(self):
        from features.functional.core.case_budget import format_duration_ms

        assert format_duration_ms(None) == "—"

    def test_ms_and_seconds(self):
        from features.functional.core.case_budget import format_duration_ms

        assert format_duration_ms(850) == "850ms"
        assert format_duration_ms(32_000) == "32s"
        assert format_duration_ms(32_500) == "32.5s"

    def test_minutes(self):
        from features.functional.core.case_budget import format_duration_ms

        assert format_duration_ms(192_000) == "3m 12s"
        assert format_duration_ms(180_000) == "3m"
        assert format_duration_ms(3_900_000) == "1h 05m"


class TestWallclockBudget:
    def test_short_case_uses_base(self, monkeypatch):
        import config
        from features.functional.core.case_budget import wallclock_timeout_s

        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_TIMEOUT_S", 240)
        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_LONG_S", 600)
        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_MAX_S", 900)
        monkeypatch.setattr(config.settings, "TEST_CASE_LONG_STEP_THRESHOLD", 6)
        assert wallclock_timeout_s(step_count=3) == 240

    def test_long_case_uses_long_budget(self, monkeypatch):
        import config
        from features.functional.core.case_budget import wallclock_timeout_s

        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_TIMEOUT_S", 240)
        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_LONG_S", 600)
        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_MAX_S", 900)
        monkeypatch.setattr(config.settings, "TEST_CASE_LONG_STEP_THRESHOLD", 6)
        assert wallclock_timeout_s(step_count=8) == 600

    def test_reassign_uses_max(self, monkeypatch):
        import config
        from features.functional.core.case_budget import wallclock_timeout_s, budget_for_case

        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_TIMEOUT_S", 240)
        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_LONG_S", 600)
        monkeypatch.setattr(config.settings, "TEST_CASE_WALLCLOCK_MAX_S", 900)
        assert wallclock_timeout_s(step_count=3, reassign_count=1) == 900
        b = budget_for_case([{}] * 8, reassign_count=1)
        assert b["wallclock_timeout_s"] == 900
        assert "m" in b["wallclock_label"] or "h" in b["wallclock_label"]


class TestWatchdogLongCaseRoom:
    def test_stale_ignored_before_min_elapsed(self, monkeypatch):
        import config
        from features.functional.core.supervisor.watchdog import LaneWatchdog

        monkeypatch.setattr(config.settings, "SLOW_CASE_MS", 600_000)
        monkeypatch.setattr(config.settings, "LANE_HEARTBEAT_S", 90.0)
        monkeypatch.setattr(config.settings, "WATCHDOG_MIN_ELAPSED_BEFORE_STALE_S", 90.0)
        wd = LaneWatchdog()
        wd.start_case(test_case_id=1, lane_id=2)
        w = wd._active[1]
        # Quiet for 100s but only 40s into the case — should not stale-reassign.
        w.started_at -= 40
        w.last_heartbeat_at -= 100
        d = wd.evaluate(1)
        assert d.action == "ok"

    def test_stale_after_min_elapsed(self, monkeypatch):
        import config
        from features.functional.core.supervisor.watchdog import LaneWatchdog

        monkeypatch.setattr(config.settings, "SLOW_CASE_MS", 600_000)
        monkeypatch.setattr(config.settings, "LANE_HEARTBEAT_S", 90.0)
        monkeypatch.setattr(config.settings, "WATCHDOG_MIN_ELAPSED_BEFORE_STALE_S", 90.0)
        wd = LaneWatchdog()
        wd.start_case(test_case_id=1, lane_id=2)
        w = wd._active[1]
        w.started_at -= 120
        w.last_heartbeat_at -= 100
        d = wd.evaluate(1)
        assert d.action == "reassign"
        assert "stale_heartbeat" in d.reason
