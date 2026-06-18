"""Lightweight HTTP reachability check before browser agent runs."""
from __future__ import annotations

from typing import Optional, Tuple

import httpx


async def verify_app_url_reachable(url: str) -> Tuple[bool, Optional[str]]:
    """
    Verify the application URL responds before launching a browser agent.
    Returns (ok, error_message).
    """
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=12.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(
                url,
                headers={"User-Agent": "QAstra-IntegrityCheck/1.0"},
            )
        if r.status_code >= 500:
            return (
                False,
                f"Server returned HTTP {r.status_code} — the application may be down or misconfigured.",
            )
        return True, None
    except httpx.ConnectError as e:
        return (
            False,
            f"Could not connect to the application ({e!s}). Check that the URL is correct and the server is running.",
        )
    except httpx.UnsupportedProtocol:
        return False, "Invalid URL (unsupported protocol)."
    except httpx.TimeoutException:
        return False, "Request timed out — the application did not respond in time."
    except httpx.HTTPError as e:
        return False, f"Could not reach the application: {e!s}"
