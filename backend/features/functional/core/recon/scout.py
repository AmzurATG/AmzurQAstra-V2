"""One-shot recon scout: login + compact DOM outline for executor hints."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from browser_use import Browser, BrowserProfile

from common.utils.logger import logger
from config import settings
from features.functional.core.browser.chrome_automation_args import default_browser_chrome_args


def _compact_outline(elements: List[Dict[str, Any]], *, limit: int = 40) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for el in elements[:limit]:
        if not isinstance(el, dict):
            continue
        out.append(
            {
                "tag": el.get("tag") or el.get("tag_name"),
                "role": el.get("role"),
                "name": (el.get("name") or el.get("text") or "")[:80],
                "type": el.get("type"),
                "href": (el.get("href") or "")[:120] or None,
            }
        )
    return out


async def run_recon_scout(
    *,
    app_url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_google_signin: bool = False,
    headless: bool = True,
    timeout_s: Optional[float] = None,
) -> Dict[str, Any]:
    """Login (best-effort) and capture a compact interactive DOM outline.

    On failure returns ``ok=False`` with an error string — callers continue
    unless auth is completely broken (``auth_broken=True``).
    """
    timeout = float(timeout_s if timeout_s is not None else getattr(settings, "RECON_TIMEOUT_S", 90) or 90)
    cache: Dict[str, Any] = {
        "ok": False,
        "app_url": app_url,
        "url": None,
        "title": None,
        "dom_outline": [],
        "auth_attempted": bool(username and password and not use_google_signin),
        "auth_broken": False,
        "error": None,
    }

    async def _scout() -> Dict[str, Any]:
        browser = Browser(
            browser_profile=BrowserProfile(
                headless=headless,
                is_local=True,
                disable_security=True,
                args=default_browser_chrome_args(),
                enable_default_extensions=settings.BROWSER_USE_DEFAULT_EXTENSIONS,
                keep_alive=False,
            )
        )
        try:
            await browser.start()
            page = await browser.get_current_page()
            if page is None:
                # browser-use API variance — try navigate via session
                session = getattr(browser, "browser_session", None) or getattr(browser, "session", None)
                if session and hasattr(session, "navigate_to"):
                    await session.navigate_to(app_url)
                    page = await browser.get_current_page()
            if page is not None and hasattr(page, "goto"):
                await page.goto(app_url, wait_until="domcontentloaded", timeout=30_000)
            url = None
            title = None
            try:
                if page is not None:
                    url = page.url if hasattr(page, "url") else None
                    title = await page.title() if hasattr(page, "title") else None
            except Exception:
                pass

            outline: List[Dict[str, Any]] = []
            try:
                if page is not None and hasattr(page, "evaluate"):
                    raw = await page.evaluate(
                        """() => {
                          const els = Array.from(document.querySelectorAll(
                            'a,button,input,select,textarea,[role="button"],[role="link"],[role="textbox"]'
                          )).slice(0, 60);
                          return els.map(el => ({
                            tag: el.tagName.toLowerCase(),
                            role: el.getAttribute('role'),
                            name: (el.innerText || el.getAttribute('aria-label') || el.name || el.id || '').trim().slice(0, 80),
                            type: el.getAttribute('type'),
                            href: el.href || null,
                          }));
                        }"""
                    )
                    if isinstance(raw, list):
                        outline = _compact_outline(raw)
            except Exception as exc:
                logger.warning("[Recon] DOM outline capture failed: %s", exc)

            # Best-effort credential fill — never blocks recon cache.
            auth_broken = False
            if username and password and not use_google_signin and page is not None:
                try:
                    await page.evaluate(
                        """(creds) => {
                          const user = document.querySelector('input[type="email"],input[type="text"],input[name*="user" i],input[name*="email" i]');
                          const pass = document.querySelector('input[type="password"]');
                          if (user) { user.focus(); user.value = creds.u; user.dispatchEvent(new Event('input', {bubbles:true})); }
                          if (pass) { pass.focus(); pass.value = creds.p; pass.dispatchEvent(new Event('input', {bubbles:true})); }
                          const btn = document.querySelector('button[type="submit"],input[type="submit"],button');
                          if (btn) btn.click();
                        }""",
                        {"u": username, "p": password},
                    )
                    await asyncio.sleep(2)
                    try:
                        url = page.url if hasattr(page, "url") else url
                        title = await page.title() if hasattr(page, "title") else title
                    except Exception:
                        pass
                except Exception as exc:
                    logger.warning("[Recon] login attempt failed: %s", exc)
                    # Only mark auth broken if we could not even reach the page.
                    if not outline and not url:
                        auth_broken = True

            return {
                "ok": True,
                "app_url": app_url,
                "url": url,
                "title": title,
                "dom_outline": outline,
                "auth_attempted": bool(username and password and not use_google_signin),
                "auth_broken": auth_broken,
                "error": None,
            }
        finally:
            try:
                await browser.kill()
            except Exception:
                pass

    try:
        return await asyncio.wait_for(_scout(), timeout=timeout)
    except asyncio.TimeoutError:
        cache["error"] = f"recon_timeout_{int(timeout)}s"
        logger.warning("[Recon] timed out after %ss", timeout)
        return cache
    except Exception as exc:
        cache["error"] = str(exc)[:300]
        logger.warning("[Recon] failed: %s", exc)
        return cache


def format_recon_prompt_hint(cache: Optional[Dict[str, Any]]) -> str:
    if not cache or not cache.get("ok"):
        return ""
    lines = ["RECON CONTEXT (from pre-run scout — use as orientation only):"]
    if cache.get("url"):
        lines.append(f"- Current URL observed: {cache['url']}")
    if cache.get("title"):
        lines.append(f"- Page title: {cache['title']}")
    outline = cache.get("dom_outline") or []
    if outline:
        lines.append("- Interactive elements (sample):")
        for el in outline[:25]:
            tag = el.get("tag") or "?"
            name = el.get("name") or ""
            role = el.get("role") or ""
            lines.append(f"  • <{tag}> {role} {name}".strip())
    return "\n".join(lines)
