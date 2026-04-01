"""
Test Execution Prompt — instructs the browser-use agent to execute test cases
with a "Goal-Oriented" mindset, prioritizing visual truth and intent over literal steps.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

# Title / description / preconditions hints that the case must use step literals, not vault creds
_NEGATIVE_CREDENTIAL_PHRASES: tuple[str, ...] = (
    "invalid password",
    "invalid login",
    "wrong password",
    "incorrect password",
    "login fail",
    "fail login",
    "failed login",
    "negative test",
    "negative testing",
    "unregistered",
    "wrong email",
    "invalid email",
    "incorrect email",
    "not registered",
    "invalid credentials",
    "wrong credentials",
    "incorrect credentials",
    "unauthorized",
    "unauthorised",
    "authentication fail",
    "auth fail",
    "must fail",
    "should fail",
    "expect error",
    "without registering",
    "non-existent user",
    "nonexistent user",
    "bad password",
    "fake password",
    "incorrect user",
    "incorrect password",
    "invalid email address",
    "bad credentials",
    "attempt login with invalid",
)

# Step value snippets that imply intentional wrong / dummy input (do not substitute secrets)
_LITERAL_VALUE_MARKERS: tuple[str, ...] = (
    "incorrect",
    "wrong-password",
    "wrongpassword",
    "bad-password",
    "badpassword",
    "invalidpass",
    "invalid-password",
    "notvalid",
    "fakepassword",
    "dummy123",
    "incorrect-password",
)


def should_inject_project_credentials(
    title: str,
    description: str,
    preconditions: str,
    steps: list[dict],
) -> bool:
    """
    When False: browser-use must not receive sensitive_data substitutions — the agent
    types exact Values from steps (negative login, wrong password, etc.).
    """
    blob = f"{title} {description} {preconditions}".lower()
    if any(p in blob for p in _NEGATIVE_CREDENTIAL_PHRASES):
        return False
    for s in steps:
        v = (s.get("value") or "").lower()
        if v and any(m in v for m in _LITERAL_VALUE_MARKERS):
            return False
        # Negative intent often lives only in step text (e.g. "invalid email", "incorrect password")
        step_blob = " ".join(
            str(s.get(k) or "")
            for k in ("description", "expected_result", "target", "action")
        ).lower()
        if any(p in step_blob for p in _NEGATIVE_CREDENTIAL_PHRASES):
            return False
    return True


TEST_EXECUTION_PROMPT = """You are a Senior QA Automation Engineer powered by advanced Vision.
Your mission is to fulfill the **Test Intent** described below. 

## APPLICATION UNDER TEST (CRITICAL)
**Base URL:** {app_url}
Use this URL whenever a step target uses a placeholder host (e.g. example.com) or when you must open or return to the app. The first navigate step should go to the real URL under test, not a template.

## THE MISSION (CRITICAL)
Title: {title}
Description: {description}
Preconditions: {preconditions}

## THE GUIDE (STEPS)
These steps are a guide, not a straightjacket. If the UI has changed or a step is technically inaccurate but the GOAL is reachable, you MUST adapt.
{steps_formatted}

## CORE RULES FOR INTELLIGENT EXECUTION

1. **VISUAL TRUTH OVER LITERAL STRINGS**:
   - If a step says "Verify URL ends in /dashboard" but you visually see a Dashboard (Logout button, User Profile, Work Queue), the step is **PASSED**. 
   - Trust your eyes (the screenshot) more than the URL or the DOM.

2. **INTENT-BASED ADAPTATION**:
   - For **positive** flows: if you click "Login" and the page shows a "Welcome" message or a "Dashboard" header, you have succeeded.
   - For **negative** flows (invalid credentials, must stay on login): reaching a logged-in dashboard means you **failed** the mission — the guide expects an error or unchanged login state.
   - If a selector (item index) is wrong, search the page for the element by text, label, or visual appearance.

3. **HANDLE INTERFERENCE PROACTIVELY**:
   - If a "Save Password", "Allow Notifications", or "Cookie Banner" popup appears, **DISMISS IT IMMEDIATELY** using your best judgment. This is considered part of "maintaining the environment" and does not fail the test.

4. **NEGATIVE TESTING INTELLIGENCE**:
   - If the mission is to test a failure (e.g., "Invalid Login"), seeing an error message is a **VICTORY (PASSED)**. Do not report it as a failure.

5. **AUTH / LOGIN ERROR TEXT (EQUIVALENCE)**:
   - For `assert_text` or "error message reads X" steps, the **real app** may use different wording than the guide (e.g. guide says "Invalid email or password" but UI shows "Invalid credentials." or "Email not registered").
   - If the visible message clearly indicates **authentication or login failure** (wrong credentials, unknown user, generic login error), mark that step **PASSED** and put the **exact on-screen text** in `actual_result` plus a short `adaptation` (e.g. "Expected phrase X; UI showed Y — semantically equivalent auth error").
   - Do **not** fail the mission over minor wording differences when the user-visible outcome matches the **intent** (login blocked + error shown).

6. **VERIFICATION LOOP**:
   - After every major action (Click, Fill, Navigate), take a moment to analyze the new state. 
   - Ask yourself: "Does this look like the state described in the next step?" If yes, proceed. If no, analyze why and try to fix it (e.g., re-click, wait, or scroll).

7. **AUTHENTICATION & INPUT VALUES**:
{auth_section}

## OUTPUT FORMAT (STRONGLY PREFERRED — RUNNER PARSES THIS)
Embed a JSON block between the exact markers below in your **final** message when possible. If you truly cannot, finish with `done(success=True)` only when the **mission intent** is satisfied — the runner may still accept successful completion.

**Rules:**
- Include **exactly {total_steps}** objects in `"steps"` with `step_number` 1 through {total_steps} (one per guide step).
- Each step: `"status"` is `"passed"` or `"failed"`, plus `"actual_result"` (string) and `"adaptation"` (string or null).
- Set `"overall"` to `"passed"` when the **mission intent** succeeded (URL/visual/auth-error equivalence rules above).
- Put a **short** prose summary inside `"summary"`.
- The markers and JSON should appear **in your final output text** (e.g. inside the same final message as `done`), not only mentally.

VERDICT_JSON_START
{{
  "steps": [
    {{
      "step_number": 1,
      "status": "passed",
      "actual_result": "...",
      "adaptation": null
    }}
  ],
  "overall": "passed",
  "summary": "How the mission was accomplished and any adaptations."
}}
VERDICT_JSON_END
"""


def build_auth_section(
    username: str | None,
    password: str | None,
    use_google_signin: bool = False,
    *,
    inject_project_secrets: bool = True,
) -> str:
    if use_google_signin:
        return (
            "Authentication: Google Sign-In\n"
            "  • Click the Google / SSO sign-in button.\n"
            f"  • Preferred account: {username or '(select work account)'}\n"
            "  • Do not type passwords into the app's own login form.\n"
        )
    if username and password and inject_project_secrets:
        return (
            "## Project credentials (positive / happy-path login)\n"
            "When a step asks for the **valid** application user/password, use these — the runtime will fill secrets when you use the placeholders:\n"
            f"  - Email/Username: {username}\n"
            f"  - Password: (stored securely)\n"
            "\n"
            "Typing instructions:\n"
            "  - For **valid** login fields, use `input_text` with exactly: <secret>username</secret> and <secret>password</secret>\n"
            "  - If a step's **→ Value:** line shows a different string (wrong password, example email, etc.), type that **literal** text instead — do not use the placeholders for that field.\n"
        )
    if username and password and not inject_project_secrets:
        return (
            "## Literal values only (negative or special-case tests)\n"
            "Type the **exact** strings from each step's **→ Value:** line using `input_text`. Do **not** substitute the project's real password or email unless the step text explicitly asks for them.\n"
            "Reaching a logged-in dashboard when the mission expects **login failure** or **stay on login** means the run **failed**.\n"
        )
    return "Authentication: No project credentials — use only the values written in the guide steps.\n"


def _rewrite_url_host_to_match_app(target_url: str, app_url: str) -> str:
    """If target is absolute and host differs from app_url's host, use app host + target path/query."""
    t = (target_url or "").strip()
    base = (app_url or "").strip()
    if not t.startswith(("http://", "https://")) or not base:
        return target_url
    if "://" not in base:
        base = "https://" + base.lstrip("/")
    pt = urlparse(t)
    pb = urlparse(base)
    if not pt.netloc or not pb.netloc:
        return target_url
    if pt.netloc.lower() == pb.netloc.lower():
        return target_url
    merged = pt._replace(scheme=pb.scheme or pt.scheme or "https", netloc=pb.netloc)
    return urlunparse(merged)


def _clean_target(target: str, app_url: str = "") -> str:
    """Replace placeholder URLs, align hosts to app_url, strip CSS selector syntax."""
    if not target:
        return target

    base_url = (app_url or "").strip()
    placeholder_domains = ["example.com", "example.org", "test.com", "localhost"]
    for domain in placeholder_domains:
        if domain in target:
            if not base_url:
                return target
            base = base_url.rstrip("/")
            path = re.sub(r"https?://[^/]+", "", target)
            return f"{base}{path}" if path else base

    if target.strip().startswith(("http://", "https://")) and base_url:
        return _rewrite_url_host_to_match_app(target.strip(), base_url)

    if re.match(r"^\[.*\]$", target) or target.startswith("#") or target.startswith("."):
        readable = re.sub(r"\[data-testid=['\"]?([^'\"\\]]+)['\"]?\]", r"the \1 element", target)
        readable = readable.replace("-", " ").replace("_", " ")
        return readable

    return target


def format_steps_for_prompt(steps: list[dict], app_url: str | None = None) -> str:
    app_url = (app_url or "").strip()
    lines: list[str] = []
    for s in steps:
        n = s["step_number"]
        action = s.get("action", "custom")
        desc = s.get("description", "")
        target = _clean_target(s.get("target", ""), app_url)
        value = s.get("value", "")
        expected = s.get("expected_result", "")

        line = f"Step {n} [{action}]: {desc}"
        if target:
            line += f"\n   → Target: {target}"
        if value:
            line += f"\n   → Value: {value}"
        if expected:
            line += f"\n   → Expected: {expected}"
        lines.append(line)

    return "\n\n".join(lines)
