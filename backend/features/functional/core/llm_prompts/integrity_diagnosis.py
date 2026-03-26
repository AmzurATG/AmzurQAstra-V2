"""
LLM Prompt Templates — Integrity Check

Prompt templates used during integrity check execution:

1. LOGIN_FORM_DETECTION  — Given raw HTML, identify the login form selectors.
2. STEP_FAILURE_DIAGNOSIS — Given a failed step's context, diagnose the failure
                            and suggest a corrected Playwright selector or action.
3. LOGIN_FAILURE_DIAGNOSIS — Same as (2) for the login phase (no test case title).
"""

# ---------------------------------------------------------------------------
# Login Form Detection
# ---------------------------------------------------------------------------

LOGIN_FORM_DETECTION_SYSTEM = """\
You are a web automation expert.
Given HTML from a login page, identify the CSS selectors for the
username field, password field, and submit button.

Always respond with valid JSON in this exact format:
{
  "username_selector": "<css selector>",
  "password_selector": "<css selector>",
  "submit_selector": "<css selector>",
  "confidence": <0-100 integer>,
  "notes": "<optional short note>"
}

Rules:
- Prefer specific, stable selectors: id > name attribute > type > placeholder.
- If a field cannot be identified, set its value to null.
- Do NOT include markdown code blocks — return raw JSON only.
"""

LOGIN_FORM_DETECTION_USER = """\
Page URL: {url}

Page HTML (truncated to first 8000 chars):
{html}

Identify the login form selectors.
"""


# ---------------------------------------------------------------------------
# Step Failure Diagnosis
# ---------------------------------------------------------------------------

STEP_FAILURE_DIAGNOSIS_SYSTEM = """\
You are a senior QA automation engineer reviewing a failed Playwright test step.
Given the step details, optional page screenshot, network activity summary,
and the state of the page at the time of failure, explain in plain English:
1. Why the step likely failed.
2. What the correct selector or approach should be.
3. A ready-to-use Playwright Python snippet to fix the step (max 3 lines).

Keep your response concise (max 200 words). Do NOT use markdown headers — use
plain text paragraphs only.
"""

STEP_FAILURE_DIAGNOSIS_USER = """\
Test Case: {test_case_title}
Step #{step_number} — Action: {action}
Target selector: {target}
Value: {value}
Error message: {error}

Current page URL: {current_url}
Page title: {page_title}

Recent network activity (last requests, truncated):
{network_log}

Page HTML snippet (first 4000 chars):
{html_snippet}

Diagnose the failure and provide a fix.
"""


LOGIN_FAILURE_DIAGNOSIS_USER = """\
Phase: Application login (integrity check)
Error message: {error}

Current page URL: {current_url}

Recent network activity (last requests, truncated):
{network_log}

Page HTML snippet (first 4000 chars):
{html_snippet}

Diagnose why login likely failed and suggest the next automation steps.
"""


def build_login_detection_prompt(url: str, html: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for login form detection."""
    return (
        LOGIN_FORM_DETECTION_SYSTEM,
        LOGIN_FORM_DETECTION_USER.format(url=url, html=html[:8000]),
    )


def build_failure_diagnosis_prompt(
    test_case_title: str,
    step_number: int,
    action: str,
    target: str,
    value: str,
    error: str,
    current_url: str,
    page_title: str,
    html_snippet: str,
    network_log_summary: str = "",
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for step failure diagnosis."""
    return (
        STEP_FAILURE_DIAGNOSIS_SYSTEM,
        STEP_FAILURE_DIAGNOSIS_USER.format(
            test_case_title=test_case_title,
            step_number=step_number,
            action=action,
            target=target or "N/A",
            value=value or "N/A",
            error=error or "Unknown error",
            current_url=current_url,
            page_title=page_title,
            html_snippet=html_snippet[:4000],
            network_log=network_log_summary or "(not available)",
        ),
    )


def build_login_failure_diagnosis_prompt(
    error: str,
    current_url: str,
    html_snippet: str,
    network_log_summary: str = "",
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for login failure diagnosis."""
    return (
        STEP_FAILURE_DIAGNOSIS_SYSTEM,
        LOGIN_FAILURE_DIAGNOSIS_USER.format(
            error=error or "Unknown error",
            current_url=current_url,
            html_snippet=html_snippet[:4000],
            network_log=network_log_summary or "(not available)",
        ),
    )
