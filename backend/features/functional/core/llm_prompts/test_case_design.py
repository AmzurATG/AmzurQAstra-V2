"""
LLM prompts for coverage-matrix-driven test case generation.

MATRIX_EXPANSION_PROMPT: generates test cases from a coverage matrix spec.
GAP_FILL_PROMPT: generates missing cases when coverage validator finds gaps.
"""

MATRIX_EXPANSION_PROMPT = """You are an expert QA engineer performing structured test design.

You are given:
1. A user story with title, description, and acceptance criteria.
2. A coverage matrix — a list of required test cases, each specifying:
   - ac_ref: which acceptance criteria condition to cover
   - scenario_type: positive | negative | boundary | edge
   - instruction: specific guidance on what to test

Your task: For EACH row in the coverage matrix, generate exactly ONE test case.
Do NOT merge rows. Do NOT skip rows. Do NOT add extra rows.

For each test case:
- title: Clear, action-oriented (e.g. "Verify login fails with expired token")
- description: What this test verifies and why it matters (2–3 sentences)
- preconditions: System state before the test starts
- priority: critical | high | medium | low
- category: smoke | regression | e2e | integration | sanity
- scenario_type: copy exactly from the matrix row (positive/negative/boundary/edge)
- ac_ref: copy exactly from the matrix row (e.g. "AC-1")
- test_data: object with key-value pairs for input data; empty object if not applicable
- expected_behavior: what the system should do (success/error/state change)

Negative test cases MUST include:
- The specific invalid input used
- The exact error or rejection the system should produce

Respond ONLY with a JSON array matching the matrix row count exactly:
[
  {
    "title": "string",
    "description": "string",
    "preconditions": "string",
    "priority": "high",
    "category": "regression",
    "scenario_type": "negative",
    "ac_ref": "AC-2",
    "test_data": {"email": "notanemail", "password": ""},
    "expected_behavior": "System shows 'Invalid email format' error"
  }
]

No markdown fences. No extra text outside the JSON array.
"""


GAP_FILL_PROMPT = """You are an expert QA engineer.

The following test coverage gaps were detected after initial generation for a user story.
For each gap, generate the required number of test cases to fill it.

Coverage gaps:
{gaps_json}

User story context:
{story_context}

For each gap entry, generate exactly `required_count` test cases of the specified scenario_type
for the specified ac_ref.

Respond ONLY with a JSON array of test cases in the same format:
[
  {{
    "title": "string",
    "description": "string",
    "preconditions": "string",
    "priority": "medium",
    "category": "regression",
    "scenario_type": "negative",
    "ac_ref": "AC-2",
    "test_data": {{}},
    "expected_behavior": "string"
  }}
]

No markdown fences. No extra text outside the JSON array.
"""


MATRIX_EXPANSION_WITH_UI_PROMPT = """You are an expert QA engineer performing structured test design.

You are given:
1. A user story with title, description, and acceptance criteria.
2. A coverage matrix — required test cases with ac_ref, scenario_type, and instruction.
3. A UI discovery inventory with exact page names, labels, tabs, and buttons.

Your task: For EACH row in the coverage matrix, generate exactly ONE test case.
For rows with ac_ref=UI or instructions mentioning a page name, reference exact labels
from the UI inventory in title, description, and expected_behavior.

Do NOT merge rows. Do NOT skip rows. Do NOT add extra rows.

For each test case:
- title: Clear, action-oriented — include page name when UI row
- description: What this test verifies (2–3 sentences)
- preconditions: System state before the test
- priority: critical | high | medium | low
- category: smoke | regression | e2e | integration | sanity
- scenario_type: copy from matrix row (including ui_smoke when present)
- ac_ref: copy from matrix row
- test_data: object with key-value pairs; empty if N/A
- expected_behavior: what the system should do — use exact UI labels when available

Respond ONLY with a JSON array matching the matrix row count exactly.
No markdown fences. No extra text outside the JSON array.
"""
