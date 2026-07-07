"""
Steel Session Client — creates and releases Steel.dev cloud browser sessions.

Steel provides a managed CDP endpoint so browser-use can attach to a remote
Chrome browser instead of launching a local process.

Key detail: Steel's session-create response returns a websocket URL that does
NOT include the API key.  The authenticated CDP URL must be constructed as:
    wss://connect.steel.dev?apiKey=<STEEL_API_KEY>&sessionId=<SESSION_ID>

Usage:
    client = SteelSessionClient()
    session = await client.create_session(run_id="run-42")
    # session.cdp_url  → authenticated wss:// URL ready for BrowserSession
    # session.viewer_url → live Steel viewer (open in browser to watch)
    try:
        ...
    finally:
        await client.release_session(session.session_id)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Steel's WebSocket proxy host — CDP connections go here with auth in query params.
_STEEL_CDP_HOST = "wss://connect.steel.dev"


class SteelApiError(Exception):
    """Raised when the Steel API returns an unexpected response."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SteelSession:
    """Immutable value object returned by SteelSessionClient.create_session."""

    session_id: str
    cdp_url: str       # Authenticated wss:// URL for BrowserSession(cdp_url=...)
    viewer_url: str    # Steel live-viewer URL (log this for monitoring)


class SteelSessionClient:
    """Thin async HTTP wrapper around the Steel Sessions API.

    Reads STEEL_API_KEY and STEEL_BASE_URL from application settings.
    Raises SteelApiError for any non-2xx response or missing configuration.
    """

    _SESSIONS_PATH = "/v1/sessions"

    def __init__(self) -> None:
        if not settings.STEEL_API_KEY:
            raise SteelApiError(
                "STEEL_API_KEY is not set. Add it to your .env or environment "
                "variables before using BROWSER_ENGINE=steel."
            )
        self._api_key = settings.STEEL_API_KEY
        self._base_url = settings.STEEL_BASE_URL.rstrip("/")
        self._headers = {
            "Steel-Api-Key": self._api_key,
            "Content-Type": "application/json",
        }

    async def create_session(self, run_id: str) -> SteelSession:
        """POST /v1/sessions — start a new Steel browser session.

        Returns a SteelSession whose cdp_url is the AUTHENTICATED wss:// URL
        (apiKey appended as a query param) required by browser-use's
        BrowserSession(cdp_url=...).

        Args:
            run_id: Identifier used to tag the session for observability.

        Raises:
            SteelApiError: If the API call fails or the response shape is
                           unexpected.
        """
        url = f"{self._base_url}{self._SESSIONS_PATH}"
        payload = {"sessionContext": {"runId": run_id}}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload, headers=self._headers)
        except httpx.RequestError as exc:
            raise SteelApiError(f"Steel API request failed: {exc}") from exc

        if resp.status_code not in (200, 201):
            raise SteelApiError(
                f"Steel API error {resp.status_code}: {resp.text[:400]}",
                status_code=resp.status_code,
            )

        data = resp.json()
        logger.debug("[SteelSessionClient] Session response keys: %s", list(data.keys()))

        session_id: Optional[str] = data.get("id") or data.get("sessionId")
        if not session_id:
            raise SteelApiError(
                f"Steel session response missing 'id'. "
                f"Got keys: {list(data.keys())} | body: {str(data)[:300]}"
            )

        # Build the authenticated CDP URL.
        # Steel's API returns a websocket_url / websocketUrl that contains the
        # base path (wss://connect.steel.dev?sessionId=...) but NO apiKey.
        # Without the key Steel's proxy returns HTTP 502 on WebSocket handshake.
        ws_url: Optional[str] = (
            data.get("websocketUrl")
            or data.get("websocket_url")
            or data.get("cdpUrl")
            or data.get("cdp_url")
        )

        if ws_url and "apiKey" not in ws_url:
            # Append authentication — Steel docs:
            # cdp_url = f"wss://connect.steel.dev?apiKey={KEY}&sessionId={ID}"
            sep = "&" if "?" in ws_url else "?"
            cdp_url = f"{ws_url}{sep}apiKey={self._api_key}"
        elif ws_url:
            cdp_url = ws_url
        else:
            # Construct from scratch using the known Steel CDP host format.
            cdp_url = f"{_STEEL_CDP_HOST}?apiKey={self._api_key}&sessionId={session_id}"

        # Viewer URL — open in browser to watch the agent live.
        viewer_url: str = (
            data.get("sessionViewerUrl")
            or data.get("session_viewer_url")
            or data.get("viewerUrl")
            or data.get("debuggerUrl")
            or f"https://app.steel.dev/sessions/{session_id}"
        )

        logger.info(
            "[SteelSessionClient] Session created: %s | viewer: %s | run=%s",
            session_id,
            viewer_url,
            run_id,
        )
        return SteelSession(
            session_id=session_id,
            cdp_url=cdp_url,
            viewer_url=viewer_url,
        )

    async def wait_for_session_ready(
        self,
        session_id: str,
        *,
        timeout_s: float = 30.0,
        poll_interval_s: float = 1.5,
    ) -> None:
        """Poll GET /v1/sessions/{id} until status indicates the browser is live.

        Steel containers start in ~2-5 s.  Without this wait browser-use's CDP
        WebSocket opens successfully but Chrome drops it immediately ("message
        handler exited unexpectedly") because Chrome isn't accepting commands yet.

        Args:
            session_id:       The Steel session ID to poll.
            timeout_s:        Maximum wait in seconds before giving up.
            poll_interval_s:  Seconds between each status check.

        Raises:
            SteelApiError: If timeout is reached without a ready status.
        """
        import asyncio
        import time

        READY_STATES = {"live", "active", "running", "created"}
        url = f"{self._base_url}{self._SESSIONS_PATH}/{session_id}"
        deadline = time.monotonic() + timeout_s
        attempt = 0

        while time.monotonic() < deadline:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, headers=self._headers)
                if resp.status_code == 200:
                    data = resp.json()
                    status: str = (
                        data.get("status") or data.get("state") or ""
                    ).lower()
                    logger.debug(
                        "[SteelSessionClient] Session %s status=%r (attempt %d)",
                        session_id,
                        status,
                        attempt,
                    )
                    if status in READY_STATES:
                        logger.info(
                            "[SteelSessionClient] Session %s ready (status=%r) after %.1fs",
                            session_id,
                            status,
                            time.monotonic() - (deadline - timeout_s),
                        )
                        return
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "[SteelSessionClient] Status poll error for %s: %s", session_id, exc
                )
            await asyncio.sleep(poll_interval_s)

        raise SteelApiError(
            f"Steel session {session_id} did not reach a ready state "
            f"within {timeout_s:.0f}s."
        )

    async def release_session(self, session_id: str) -> None:
        """DELETE /v1/sessions/{id} — terminate and release a Steel session.

        Safe to call from a finally block — errors are logged, not raised.
        """
        url = f"{self._base_url}{self._SESSIONS_PATH}/{session_id}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.delete(url, headers=self._headers)
            if resp.status_code not in (200, 204):
                logger.warning(
                    "[SteelSessionClient] Non-2xx when releasing session %s: %s %s",
                    session_id,
                    resp.status_code,
                    resp.text[:200],
                )
            else:
                logger.info("[SteelSessionClient] Session released: %s", session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[SteelSessionClient] Failed to release session %s: %s",
                session_id,
                exc,
            )
