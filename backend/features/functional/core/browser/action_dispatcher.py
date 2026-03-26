"""
Browser Action Dispatcher

Maps a test step's action string to the corresponding BrowserRunner method.
Extracted as a standalone utility so IntegrityCheckService and
TestExecutionService can both reuse it without duplicating logic.
"""
from features.functional.core.browser.base import BrowserRunner, StepActionResult
from typing import Optional


async def dispatch(
    runner: BrowserRunner,
    action: str,
    target: Optional[str],
    value: Optional[str],
) -> StepActionResult:
    """Dispatch a single test step action to the browser runner."""
    if action == "navigate":
        return await runner.navigate(target or value or "")
    if action == "click":
        return await runner.click(target or "")
    if action in ("fill", "type"):
        return await runner.fill(target or "", value or "")
    if action == "select":
        return await runner.select_option(target or "", value or "")
    if action == "hover":
        return await runner.hover(target or "")
    if action == "wait":
        ms = int(value) if value and str(value).isdigit() else 1000
        return await runner.wait(ms)
    if action == "assert_visible":
        return await runner.assert_visible(target or "")
    if action == "assert_text":
        return await runner.assert_text(target or "", value or "")
    if action == "assert_url":
        return await runner.assert_url(target or value or "")
    if action in ("check", "uncheck"):
        return await runner.click(target or "")
    # Unknown / screenshot actions — treat as no-op success
    return StepActionResult(success=True)
