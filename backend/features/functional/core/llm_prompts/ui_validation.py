"""Prompts for the UI re-check (vision) validation agent."""
from __future__ import annotations

UI_VALIDATION_SYSTEM_V1 = """You are a senior QA UI validation agent.

You review screenshots from an automated browser test and decide whether the
APPLICATION UI evidence supports a pass or fail for the stated expected steps.

Rules:
1. Judge from what is VISIBLE in the screenshots — not from the executor narrative alone.
2. If screenshots clearly show the expected UI outcome, verdict is passed.
3. If screenshots clearly show the expected outcome is missing/wrong, verdict is failed.
4. If evidence is insufficient or ambiguous, verdict is inconclusive (do not guess).
5. Output ONLY valid JSON matching the schema — no markdown fences.

JSON schema:
{
  "ui_verdict": "passed" | "failed" | "inconclusive",
  "confidence": 0.0-1.0,
  "step_checks": [
    {"step": 1, "status": "passed|failed|inconclusive", "evidence": "shot label", "why": "short"}
  ],
  "ui_observations": ["short factual notes about what the UI shows"],
  "summary": "one sentence"
}
"""


def build_ui_validation_user_prompt(
    *,
    title: str,
    description: str,
    expected_steps: list,
    executor_status: str,
    executor_summary: str = "",
) -> str:
    import json

    steps_slim = []
    for s in expected_steps or []:
        if not isinstance(s, dict):
            continue
        steps_slim.append(
            {
                "step_number": s.get("step_number"),
                "description": (s.get("description") or "")[:300],
                "expected_result": (s.get("expected_result") or "")[:300],
            }
        )
    return (
        f"Test title: {title}\n"
        f"Description: {(description or '')[:800]}\n"
        f"Executor status: {executor_status}\n"
        f"Executor summary: {(executor_summary or '')[:800]}\n\n"
        f"Expected steps:\n{json.dumps(steps_slim, indent=2)}\n\n"
        "Screenshots are attached in order (earliest → latest). "
        "Validate the UI against the expected steps and return JSON only."
    )
