"""
Merged Execution Prompt — builds a browser-use task for a group of test cases
whose duplicate steps have been merged into a single optimised script.

The agent executes the merged script (not individual case steps) and emits a
VERDICT_JSON with one entry per merged step.  The EvaluatorAgent later maps
each merged step's result back to the original per-case per-step rows.
"""
from __future__ import annotations

from features.functional.core.llm_prompts.test_execution import (
    build_auth_section,
    format_steps_for_prompt,
    should_inject_project_credentials,
)
from features.functional.core.execution.execution_plan import MergedStep

_MERGED_EXECUTION_PROMPT = """\
You are a Senior QA Automation Engineer powered by advanced Vision.
Your mission: execute the MERGED TEST SCRIPT below for a group of {total_cases} test cases.
This merged script eliminates duplicate steps (e.g. login runs once, satisfying all cases).

## APPLICATION UNDER TEST
**Base URL:** {app_url}

## GROUP: {group_label}
{auth_section}

## MERGED STEP SCRIPT
Each step covers one or more original test-case steps. Execute them in order.
{merged_steps_formatted}

## EXECUTION RULES

1. **EXECUTE ALL STEPS IN ORDER** — do not skip any merged step.
2. **VISUAL TRUTH** — trust the screenshot more than URLs or DOM text.
3. **ADAPT INTELLIGENTLY** — if the UI differs from the description but the intent is reachable, adapt and note it.
4. **DISMISS INTERFERENCE** — cookie banners, save-password dialogs, notifications → dismiss immediately.
5. **AUTH** — if a step says "login", perform the full login flow. Once logged in, stay logged in for subsequent steps unless a step says to log out.
6. **NAVIGATION RESETS** — after completing case-specific segments, navigate to reset_url before the next case segment.

## OUTPUT FORMAT
Return ONLY valid JSON between the exact markers. Include one entry per merged step.

VERDICT_JSON_START
{{
  "merged_step_results": [
    {{
      "merged_step_number": 1,
      "status": "passed",
      "actual_result": "What you observed",
      "adaptation": null
    }}
  ],
  "overall": "passed",
  "summary": "Brief summary of what was executed and any notable adaptations."
}}
VERDICT_JSON_END
"""

_RESET_CONTEXT = """\
## SESSION RESET CONTEXT
After the previous case segment, the browser is at:
  URL: {prev_url}
  Title: {prev_title}

Navigate to {reset_url} before starting this case's segment.
"""


def _format_merged_steps(merged_steps: list[MergedStep], app_url: str) -> str:
    """Format merged steps for the prompt, showing what each step satisfies."""
    lines: list[str] = []
    for ms in sorted(merged_steps, key=lambda s: s.merged_step_number):
        satisfies_str = ", ".join(
            f"TC-{s['tc_id']} step {s['step_number']}"
            for s in ms.satisfies
        )
        line = f"Merged Step {ms.merged_step_number} [{ms.action}]: {ms.description}"
        if ms.target:
            line += f"\n   → Target: {ms.target}"
        if ms.value:
            line += f"\n   → Value: {ms.value}"
        if ms.expected_result:
            line += f"\n   → Expected: {ms.expected_result}"
        if satisfies_str:
            line += f"\n   → Satisfies: {satisfies_str}"
        lines.append(line)
    return "\n\n".join(lines)


def build_merged_task_prompt(
    *,
    group_label: str,
    merged_steps: list[MergedStep],
    total_cases: int,
    app_url: str,
    username: str | None,
    password: str | None,
    use_google_signin: bool,
    prev_url: str | None = None,
    prev_title: str | None = None,
    reset_url: str | None = None,
) -> tuple[str, dict | None]:
    """
    Build the browser-use task prompt for a merged group execution.

    Returns
    -------
    (task_prompt, sensitive_data) — sensitive_data is the dict for browser-use
    credential injection, or None when credentials should not be injected.
    """
    # All shared-session groups use valid credentials (negatives are isolated)
    inject_creds = True
    auth_section = build_auth_section(
        username,
        password,
        use_google_signin,
        inject_project_secrets=inject_creds,
    )

    merged_steps_fmt = _format_merged_steps(merged_steps, app_url)

    prompt = _MERGED_EXECUTION_PROMPT.format(
        app_url=app_url,
        group_label=group_label,
        auth_section=auth_section,
        merged_steps_formatted=merged_steps_fmt,
        total_cases=total_cases,
    )

    if prev_url or prev_title:
        reset_context = _RESET_CONTEXT.format(
            prev_url=prev_url or app_url,
            prev_title=prev_title or "Unknown",
            reset_url=reset_url or app_url,
        )
        prompt = reset_context + "\n" + prompt

    sensitive_data = None
    if inject_creds and username and password and not use_google_signin:
        sensitive_data = {"username": username, "password": password}

    return prompt, sensitive_data
