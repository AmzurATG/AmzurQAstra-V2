"""
Steel.dev CDP session URL builder.

Steel hosts the browser; Playwright drives it through ``chromium.connect_over_cdp``.
See: https://docs.steel.dev/overview/guides/playwright-python
"""
from typing import Dict, Optional
from urllib.parse import urlencode

STEEL_CDP_HOST = "connect.steel.dev"
STEEL_CDP_SCHEME = "wss"


def build_steel_cdp_url(api_key: str, session_id: Optional[str] = None) -> str:
    """
    Build the WebSocket URL for Playwright ``connect_over_cdp``.

    Args:
        api_key: Steel API key (required).
        session_id: Optional UUID session id for Steel API correlation / release.

    Raises:
        ValueError: If api_key is missing or blank.
    """
    key = (api_key or "").strip()
    if not key:
        raise ValueError("STEEL_API_KEY is required to connect to Steel")

    query: Dict[str, str] = {"apiKey": key}
    if session_id and session_id.strip():
        query["sessionId"] = session_id.strip()

    qs = urlencode(query)
    return f"{STEEL_CDP_SCHEME}://{STEEL_CDP_HOST}?{qs}"
