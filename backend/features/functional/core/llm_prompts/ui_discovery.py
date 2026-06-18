"""
LLM task prompt for UI Discovery agent — explore app and emit structured inventory.
"""

UI_DISCOVERY_TASK_TEMPLATE = """You are a QA discovery agent exploring a web application to build a structured UI inventory.

Target URL: {app_url}
Actor role perspective: {actor_role}

Your mission:
1. Navigate to the target URL and observe the landing/login page.
{login_instructions}
3. After login (if applicable), explore the main navigation — visit each top-level menu item once.
4. For each page visited, record:
   - Page name (human-readable, e.g. "Login", "Leagues", "Profile")
   - URL path (e.g. "/login", "/leagues")
   - Visible input fields, buttons, links (with exact visible labels and placeholders)
   - Tabs on the page (exact tab labels)
   - Primary actions available (e.g. "Create League", "Sign Up")
5. Go one level deep into each major module (e.g. open a league detail if leagues exist).
6. Do NOT go deeper than 2 navigation levels from the dashboard/home.
7. Maximum {max_steps} browser actions total — be efficient.

RULES:
{auth_rules}
- Record ONLY what you actually see on screen — do not invent pages or elements.
- Prefer manual email/password login over Google SSO when both exist.
- Take note of main navigation items for the navigation array.

MANDATORY OUTPUT — your final message MUST include this exact block:
INVENTORY_JSON_START
{{
  "platform": "web",
  "actor_role": "{actor_role}",
  "app_url": "{app_url}",
  "discovered_at": "<ISO8601 timestamp>",
  "pages": [
    {{
      "name": "Login",
      "url": "/login",
      "elements": [{{"type": "input", "label": "Email", "placeholder": "Enter email"}}],
      "tabs": [],
      "actions": ["Sign In"],
      "screenshot_path": null
    }}
  ],
  "navigation": ["Leagues", "Profile"],
  "modules_inferred": ["Authentication", "Leagues"]
}}
INVENTORY_JSON_END

The JSON must be valid. Include every page you visited. End your run after emitting INVENTORY_JSON_END.
"""

UI_DISCOVERY_REPAIR_PROMPT = """The following text was supposed to contain valid JSON between INVENTORY_JSON_START and INVENTORY_JSON_END but parsing failed.

Extract or repair the inventory JSON. Return ONLY the corrected JSON object (no markers, no markdown):
{raw_text}
"""
