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

1. **EXECUTE ALL STEPS IN ORDER** — do not skip any merged step. Return a status for EVERY merged step.
2. **GROUND TRUTH** — trust what you actually observe on the page (the DOM, and the screenshot when one is available) over the literal wording of the step.
3. **CAPTURE THE INTENT, THEN ADAPT (self-healing)** — each step describes an INTENT, not an exact script. If the literal target/selector/label does not match the live UI, find the element that fulfils the same intent (different selector, renamed button, alternate path) and use it. A step only FAILS when its intent is genuinely unreachable — not because the literal locator changed.
4. **RECORD EVERY ADAPTATION** — whenever the actions you took differed from the literal step (different selector, extra navigation, alternate element, recovered from an error), set this step's `"adaptation"` to a short sentence describing what you changed and why. Set `"adaptation": null` ONLY when you executed the step exactly as written.
5. **DISMISS INTERFERENCE** — cookie banners, save-password dialogs, notifications → dismiss immediately.
6. **AUTH** — if a step says "login", perform the full login flow. Once logged in, stay logged in for subsequent steps unless a step says to log out. For a negative-login step, enter the specified wrong values, confirm the error, then continue.
7. **NAVIGATION RESETS** — after completing case-specific segments, navigate to reset_url before the next case segment.

## OUTPUT FORMAT
Return ONLY valid JSON between the exact markers. Include one entry per merged step.
For each step: status is one of "passed" | "failed" | "skipped" | "error"; actual_result describes
what you observed; adaptation is a short string when you deviated from the literal step, else null.

VERDICT_JSON_START
{{
  "merged_step_results": [
    {{
      "merged_step_number": 1,
      "status": "passed",
      "actual_result": "What you observed",
      "adaptation": "Clicked the 'Sign in' button — the step said 'Login' but no such label existed"
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


_SEGMENT_PROMPT = """\
You are a Senior QA Automation Engineer driving an ALREADY-OPEN browser session.
{position_context}

## APPLICATION UNDER TEST
**Base URL:** {app_url}
{auth_section}

## EXECUTE EXACTLY THIS ONE STEP (step {index} of {total})
{step_block}

## RULES
1. Do ONLY this step. Do NOT run ahead to later steps.
2. CAPTURE THE INTENT: the step is an intent, not a literal script. If the target/label/selector
   does not match the live UI, find the element that fulfils the same intent and use it.
3. Dismiss any cookie banner / save-password / notification popup that blocks you.
4. The step FAILS only if its intent is genuinely unreachable — not because a locator changed.

## OUTPUT — your FINAL message must end with exactly one line in this format:
STEP_VERDICT: PASS — <short observation>[ | ADAPTED: <what you changed and why>]
or
STEP_VERDICT: FAIL — <what went wrong>
"""


def build_segment_task_prompt(
    *,
    merged_step: MergedStep,
    index: int,
    total: int,
    app_url: str,
    username: str | None,
    password: str | None,
    use_google_signin: bool,
    is_first: bool,
) -> tuple[str, dict | None]:
    """Build a focused browser-use task for a SINGLE merged step (segmented execution)."""
    inject_creds = True
    auth_section = build_auth_section(
        username, password, use_google_signin, inject_project_secrets=inject_creds
    )

    satisfies_str = ", ".join(
        f"TC-{s['tc_id']} step {s['step_number']}" for s in merged_step.satisfies
    )
    parts = [f"[{merged_step.action}] {merged_step.description}"]
    if merged_step.target:
        parts.append(f"   → Target: {merged_step.target}")
    if merged_step.value:
        parts.append(f"   → Value: {merged_step.value}")
    if merged_step.expected_result:
        parts.append(f"   → Expected: {merged_step.expected_result}")
    if satisfies_str:
        parts.append(f"   → Covers: {satisfies_str}")
    step_block = "\n".join(parts)

    if is_first:
        position_context = (
            "This is the FIRST step of the group. Navigate to the application and perform "
            "any required login as instructed by the step."
        )
    else:
        position_context = (
            "Earlier steps in this group have ALREADY run in this same browser. Continue from "
            "the CURRENT page state — do not re-login or re-navigate unless this step says to."
        )

    prompt = _SEGMENT_PROMPT.format(
        position_context=position_context,
        app_url=app_url,
        auth_section=auth_section,
        index=index,
        total=total,
        step_block=step_block,
    )

    sensitive_data = None
    if inject_creds and username and password and not use_google_signin:
        sensitive_data = {"username": username, "password": password}

    return prompt, sensitive_data


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
