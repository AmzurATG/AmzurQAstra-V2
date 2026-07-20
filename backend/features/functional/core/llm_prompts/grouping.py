"""Prompts for semantic test-case grouping (LangGraph planner agents)."""
from __future__ import annotations

import json
from typing import Any, Dict, List


GROUPING_SYSTEM_PROMPT = """You are a Senior QA Test Architect designing an efficient execution plan.

Your job: analyze test cases and their steps, then output execution GROUPS that minimize repeated login/logout/navigation while preserving test intent.

## CRITICAL RULES
1. **Never merge assertions or the core test under verification.** Only merge setup/teardown: login, logout, navigate-to-app, cookie dismissals.
2. **Phase ordering within each group (always):**
   - `pre_auth` — negative login, invalid credentials, empty fields, lockout tests (while logged OUT)
   - `login` — one shared successful login for the group (merged step, run ONCE)
   - `authed` — all authenticated functional cases
   - `teardown` — logout / session cleanup (merged step, run ONCE at end)
3. Cases that need NO login go in their own group with phase_order `["no_auth"]`.
4. If a case MUST run in isolation (conflicts with shared session), put it alone in a group.
5. Assign each case exactly one phase via `case_phases` (keys are test_case_id strings).
6. Output ONLY valid JSON — no markdown fences.

## OUTPUT SCHEMA
{
  "groups": [
    {
      "group_id": "G1",
      "title": "Short group label",
      "phase_order": ["pre_auth", "login", "authed", "teardown"],
      "case_ids": [12, 5, 8],
      "case_phases": {"12": "pre_auth", "5": "authed", "8": "authed"},
      "merged_steps": {
        "login": {"description": "Login with valid credentials", "run_once": true},
        "logout": {"description": "Logout from application", "run_once": true}
      },
      "shared_login": true
    }
  ]
}
"""


def build_planner_user_prompt(
    cases: List[Dict[str, Any]],
    app_url: str,
) -> str:
    """Serialize a chunk of cases for the planner LLM."""
    slim: List[Dict[str, Any]] = []
    for c in cases:
        steps = c.get("steps") or []
        slim.append(
            {
                "test_case_id": c.get("test_case_id"),
                "title": c.get("title"),
                "description": (c.get("description") or "")[:500],
                "preconditions": (c.get("preconditions") or "")[:300],
                "steps": [
                    {
                        "step_number": s.get("step_number"),
                        "action": s.get("action"),
                        "description": (s.get("description") or "")[:200],
                        "expected_result": (s.get("expected_result") or "")[:200],
                    }
                    for s in steps[:30]
                ],
            }
        )
    return (
        f"Application URL: {app_url}\n\n"
        f"Analyze these {len(cases)} test case(s) and produce execution groups:\n\n"
        f"{json.dumps(slim, indent=2)}"
    )


RECON_SYSTEM_PROMPT = """You are a QA recon agent. Capture the login page structure for fast DOM-driven execution later.
Summarize interactive elements (buttons, inputs, links) with likely selectors. Keep it concise JSON."""


def build_recon_user_prompt(app_url: str, group_title: str) -> str:
    return (
        f"Group: {group_title}\nApp URL: {app_url}\n"
        "Describe login page elements and navigation entry points as JSON "
        'with keys: "url", "inputs", "buttons", "links".'
    )
