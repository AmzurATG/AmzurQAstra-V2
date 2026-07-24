"""Tests for Jira bug drafting from failed test results."""
from __future__ import annotations


class TestEligibility:
    def test_failed_ok(self):
        from features.functional.services.jira_bug_from_result import is_eligible_for_jira_bug

        ok, _ = is_eligible_for_jira_bug(status="failed")
        assert ok is True

    def test_infra_rejected(self):
        from features.functional.services.jira_bug_from_result import is_eligible_for_jira_bug

        ok, reason = is_eligible_for_jira_bug(status="failed", infra_error=True)
        assert ok is False
        assert "Infrastructure" in reason or "blocked" in reason.lower()

    def test_error_status_rejected(self):
        from features.functional.services.jira_bug_from_result import is_eligible_for_jira_bug

        ok, _ = is_eligible_for_jira_bug(status="error")
        assert ok is False

    def test_passed_rejected(self):
        from features.functional.services.jira_bug_from_result import is_eligible_for_jira_bug

        ok, _ = is_eligible_for_jira_bug(status="passed")
        assert ok is False


class TestDescriptionBuilder:
    def test_marks_failed_step(self):
        from features.functional.services.jira_bug_from_result import build_bug_description

        text = build_bug_description(
            title="Login flow",
            run_number=12,
            app_url="https://app.example",
            duration_ms=45_000,
            error_message="Button not found",
            step_results=[
                {"step_number": 1, "description": "Open login", "status": "passed"},
                {
                    "step_number": 2,
                    "description": "Click submit",
                    "status": "failed",
                    "expected_result": "Dashboard",
                    "actual_result": "Error toast",
                },
            ],
            related_story_key="PROJ-9",
        )
        assert "failed here" in text
        assert "Click submit" in text
        assert "Dashboard" in text
        assert "Error toast" in text
        assert "PROJ-9" in text
        assert "#12" in text
        assert "Button not found" in text

    def test_summary_prefix(self):
        from features.functional.services.jira_bug_from_result import build_bug_summary

        assert build_bug_summary("Checkout") == "[QAstra] Checkout failed"


class TestScreenshotResolve:
    def test_resolves_evidence_files(self, tmp_path, monkeypatch):
        import config
        from features.functional.services import jira_bug_from_result as mod

        monkeypatch.setattr(config.settings, "SCREENSHOTS_DIR", str(tmp_path))
        (tmp_path / "a.png").write_bytes(b"x")
        (tmp_path / "b.png").write_bytes(b"y")
        paths = mod.resolve_screenshot_paths(
            screenshot_path="/screenshots/a.png",
            agent_logs=[
                {"screenshot_path": "/screenshots/b.png", "evidence": True},
                {"screenshot_path": "/screenshots/missing.png", "evidence": True},
            ],
        )
        names = {p.name for p in paths}
        assert names == {"a.png", "b.png"}


class TestDraft:
    def test_draft_ineligible_infra(self):
        from features.functional.services.jira_bug_from_result import build_jira_bug_draft

        d = build_jira_bug_draft(
            title="X",
            status="failed",
            infra_error=True,
        )
        assert d["eligible"] is False

    def test_draft_eligible(self):
        from features.functional.services.jira_bug_from_result import build_jira_bug_draft

        d = build_jira_bug_draft(
            title="Pay",
            status="failed",
            run_id=1,
            step_results=[{"step_number": 1, "description": "Go", "status": "failed"}],
        )
        assert d["eligible"] is True
        assert "[QAstra]" in d["summary"]
        assert "Steps to Reproduce" in d["description"]


class TestJiraClientSprintOptional:
    def test_assign_to_sprint_noop_when_none(self):
        import asyncio
        from common.integrations.jira.client import JiraIntegration

        integ = JiraIntegration(
            config={
                "base_url": "https://example.atlassian.net",
                "email": "a@b.com",
                "api_token": "tok",
                "project_key": "PROJ",
            }
        )
        assert asyncio.run(integ.assign_to_sprint("PROJ-1", 0)) is False
