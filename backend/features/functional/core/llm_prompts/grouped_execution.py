"""
Grouped Execution Prompt — extends TEST_EXECUTION_PROMPT for shared-session runs.

When multiple test cases share a browser (login once, run N cases), the agent
receives extra context:
  - The current session state (URL + page title after the previous case).
  - A reset_before URL to navigate to before starting this case.
  - A reminder that it is already authenticated (for positive flows).

All original adaptation rules from TEST_EXECUTION_PROMPT are preserved.
"""
from __future__ import annotations

from features.functional.core.llm_prompts.test_execution import (
    TEST_EXECUTION_PROMPT,
    build_auth_section,
    format_steps_for_prompt,
    should_inject_project_credentials,
)

# Prepended to the standard prompt for shared-session cases.
_SESSION_CONTEXT_PREFIX = """\
## SHARED SESSION CONTEXT (READ CAREFULLY)
You are executing this test case inside an **ongoing browser session**.

Current browser state after previous case:
  - URL: {prev_url}
  - Page title: {prev_title}

Before starting this test case, you MUST:
1. Navigate to: {reset_before}
2. Wait until the page loads and you see the expected starting state.
3. Only then proceed with the test steps below.

Do NOT log out between cases unless this test explicitly requires it.
You are already authenticated as the valid application user.

---
"""

# Appended when the case starts from a non-authenticated state (fresh-session cases
# that somehow ended up needing the shared-session prompt — safety guard).
_FRESH_AUTH_REMINDER = """\
Note: If you find yourself on a login page unexpectedly, complete login using the
provided credentials before proceeding with the test steps.
"""


def build_grouped_task_prompt(
    *,
    title: str,
    description: str,
    preconditions: str,
    steps: list[dict],
    app_url: str,
    username: str | None,
    password: str | None,
    use_google_signin: bool,
    # Shared-session extras
    prev_url: str | None = None,
    prev_title: str | None = None,
    reset_before: str | None = None,
    is_shared_session: bool = False,
) -> str:
    """
    Build the full browser-use task prompt for a test case.

    For shared-session cases: injects the SESSION CONTEXT section above the
    standard TEST_EXECUTION_PROMPT.
    For isolated cases: returns the standard prompt unchanged.
    """
    inject_creds = should_inject_project_credentials(
        title, description or "", preconditions or "", steps
    )
    auth_section = build_auth_section(
        username,
        password,
        use_google_signin,
        inject_project_secrets=inject_creds,
    )
    steps_fmt = format_steps_for_prompt(
        [{"step_number": i + 1, **s} if "step_number" not in s else s for i, s in enumerate(steps)],
        app_url=app_url,
    )
    base_prompt = TEST_EXECUTION_PROMPT.format(
        app_url=app_url,
        auth_section=auth_section,
        title=title,
        description=description or "N/A",
        preconditions=preconditions or "None",
        steps_formatted=steps_fmt,
        total_steps=len(steps),
    )

    if not is_shared_session:
        return base_prompt

    # Build the session context prefix
    effective_reset = reset_before or app_url
    context_prefix = _SESSION_CONTEXT_PREFIX.format(
        prev_url=prev_url or app_url,
        prev_title=prev_title or "Unknown",
        reset_before=effective_reset,
    )

    return context_prefix + base_prompt
