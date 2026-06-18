"""
LLM prompts for BRD → User Story generation pipeline.

Two-pass approach:
  Pass 1 (BRD_DECOMPOSE_PROMPT):  BRD text → functional modules / themes
  Pass 2 (BRD_STORY_EXPAND_PROMPT): module list + BRD → full user stories with AC
"""

BRD_DECOMPOSE_PROMPT = """You are a senior business analyst.

Read the BRD (Business Requirements Document) and extract distinct functional modules or themes.
Each module should represent a coherent area of functionality (e.g. "User Authentication",
"Order Management", "Notifications", "Payment Processing").

Rules:
- Return between 3 and 12 modules depending on BRD complexity.
- If the BRD is small, return fewer modules — do not invent areas not mentioned.
- Each module must have a short label and a 1-sentence scope description.

Respond ONLY with a JSON array:
[
  {{
    "label": "Module Name (max 60 chars)",
    "scope": "One sentence describing what this module covers."
  }}
]

No markdown fences. No extra text outside the JSON array."""


BRD_STORY_EXPAND_PROMPT = """You are a senior business analyst writing INVEST-compliant user stories.

You are given:
1. The full BRD text.
2. A list of functional modules extracted from the BRD.

Your task: For each module, generate 2–4 user stories that together cover the module's scope.

Requirements for each user story:
- Title: "As a [role], I can [action] so that [benefit]" — max 120 characters.
- Description: 2–4 sentences expanding on the title.
- Acceptance criteria: Write 3–5 concrete, testable conditions.
  Format each condition as a numbered list: "1. [condition]".
  Each condition must be independently verifiable (no compound sentences with "and").
  At least one condition must be a validation rule (what the system must reject or prevent).
- Priority: critical | high | medium | low — based on business impact.
- Module: the module label this story belongs to.
- Rationale: 1 sentence explaining why this story is needed based on the BRD.

Respond ONLY with a JSON array of all stories across all modules:
[
  {{
    "title": "string",
    "description": "string",
    "acceptance_criteria": "1. condition\\n2. condition\\n3. condition",
    "priority": "high",
    "module": "Module Name",
    "rationale": "string"
  }}
]

No markdown fences. No extra text outside the JSON array.
Total stories across all modules: between {min_stories} and {max_stories}.
"""

BRD_UI_MERGE_PROMPT = """You are a senior business analyst merging BRD modules with UI discovery data.

You are given:
1. Functional modules extracted from a BRD document.
2. A UI discovery inventory listing pages, navigation, and inferred modules from the live app.

Your task: Produce a merged module list that covers BOTH BRD requirements AND visible UI areas.

Rules:
- Keep all BRD modules; add UI-only modules for pages/navigation items not covered by the BRD.
- For modules present in both, set source to "both" and expand scope to mention UI elements seen.
- For BRD-only modules, source = "brd".
- For UI-only modules (no BRD mention), source = "ui".
- Return between 3 and 20 merged modules.

Respond ONLY with a JSON array:
[
  {{
    "label": "Module Name",
    "scope": "One sentence covering BRD and/or UI scope.",
    "source": "brd | ui | both"
  }}
]

No markdown fences. No extra text outside the JSON array."""

BRD_STORY_EXPAND_WITH_UI_PROMPT = """You are a senior business analyst writing INVEST-compliant user stories.

You are given:
1. The full BRD text.
2. A merged module list (from BRD + UI discovery).
3. A UI discovery inventory with exact page names, labels, tabs, and navigation.

Your task:
- For each module, generate 2–4 user stories covering the module's scope.
- For each discovered page/tab in the UI inventory that has NO corresponding story yet,
  create 1–2 additional UI-grounded stories with acceptance criteria referencing exact visible labels.

Requirements for each user story:
- Title: "As a [role], I can [action] so that [benefit]" — max 120 characters.
- Description: 2–4 sentences expanding on the title.
- Acceptance criteria: Write 3–5 concrete, testable conditions with numbered list format.
  Reference exact UI labels from the inventory when testing that page.
- Priority: critical | high | medium | low.
- Module: the module label this story belongs to.
- Rationale: 1 sentence explaining why this story is needed.
- discovery_source: "brd_generated" | "ui_discovered" | "brd_ui_merged"

Respond ONLY with a JSON array:
[
  {{
    "title": "string",
    "description": "string",
    "acceptance_criteria": "1. condition\\n2. condition",
    "priority": "high",
    "module": "Module Name",
    "rationale": "string",
    "discovery_source": "brd_ui_merged"
  }}
]

No markdown fences. No extra text outside the JSON array.
Total stories: between {min_stories} and {max_stories}.
"""
