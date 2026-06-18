"""
UI Context Loader — fetch and format UI discovery inventory for generation prompts.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from features.functional.schemas.ui_discovery import UiInventory, UiPage
from features.functional.services.ui_discovery_service import UiDiscoveryService


async def get_latest_inventory(db: AsyncSession, project_id: int) -> Optional[UiInventory]:
    """Return latest completed UI inventory for a project, or None."""
    svc = UiDiscoveryService(db)
    latest = await svc.get_latest(project_id)
    if latest.found and latest.inventory:
        return latest.inventory
    return None


def format_inventory_for_prompt(inventory: UiInventory, max_pages: int = 20) -> str:
    """Compact text block suitable for LLM system/user messages."""
    lines = [
        f"UI DISCOVERY INVENTORY (platform={inventory.platform}, role={inventory.actor_role})",
        f"App URL: {inventory.app_url}",
        f"Discovered: {inventory.discovered_at}",
    ]
    if inventory.navigation:
        lines.append(f"Main navigation: {', '.join(inventory.navigation[:15])}")
    if inventory.modules_inferred:
        lines.append(f"Inferred modules: {', '.join(inventory.modules_inferred[:15])}")

    lines.append("\nPages:")
    for page in inventory.pages[:max_pages]:
        lines.append(_format_page(page))

    if len(inventory.pages) > max_pages:
        lines.append(f"... and {len(inventory.pages) - max_pages} more pages (truncated)")

    return "\n".join(lines)


def _format_page(page: UiPage) -> str:
    parts = [f"  • {page.name} ({page.url or 'no url'})"]
    if page.tabs:
        parts.append(f"    Tabs: {', '.join(page.tabs)}")
    if page.actions:
        parts.append(f"    Actions: {', '.join(page.actions)}")
    if page.elements:
        el_desc = []
        for el in page.elements[:12]:
            label = el.label or el.placeholder or el.name or el.type
            el_desc.append(f"{el.type}:{label}")
        parts.append(f"    Elements: {', '.join(el_desc)}")
    return "\n".join(parts)


def match_page_for_test_case(inventory: UiInventory, title: str, ac_text: str = "") -> Optional[UiPage]:
    """Find the inventory page most relevant to a test case by keyword overlap."""
    haystack = f"{title} {ac_text}".lower()
    best: Optional[UiPage] = None
    best_score = 0
    for page in inventory.pages:
        name = page.name.lower()
        score = 0
        if name in haystack:
            score += 3
        for token in name.split():
            if len(token) > 3 and token in haystack:
                score += 1
        for tab in page.tabs:
            if tab.lower() in haystack:
                score += 2
        if score > best_score:
            best_score = score
            best = page
    return best
