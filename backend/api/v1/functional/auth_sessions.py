"""
Auth Sessions API

Endpoints for managing encrypted browser auth sessions per project.
Supports two flows:
- Credentials: username/password encrypted and saved
- Google OAuth: launches a visible browser, user signs in manually,
  storage state is captured and encrypted
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.database import get_db
from common.db.models.user import User
from common.api.deps import get_current_active_user
from common.services.auth_session_service import AuthSessionService
from common.utils.logger import logger

router = APIRouter()


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class SaveCredentialsRequest(BaseModel):
    username: str
    password: str


class GoogleOAuthRequest(BaseModel):
    login_url: str


class AuthSessionResponse(BaseModel):
    id: int
    project_id: int
    auth_type: str
    is_active: bool
    created_at: Optional[str] = None


def _build_response(session) -> AuthSessionResponse:
    return AuthSessionResponse(
        id=session.id,
        project_id=session.project_id,
        auth_type=session.auth_type,
        is_active=session.is_active,
        created_at=session.created_at.isoformat() if session.created_at else None,
    )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/{project_id}", response_model=Optional[AuthSessionResponse])
async def get_auth_session(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the active auth session metadata (type, status). No secrets returned."""
    svc = AuthSessionService(db)
    session = await svc.get_active_session(project_id)
    if not session:
        return None
    return _build_response(session)


@router.post("/{project_id}", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
async def save_credentials_session(
    project_id: int,
    body: SaveCredentialsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Encrypt and save username/password credentials for a project."""
    svc = AuthSessionService(db)
    session = await svc.save_credentials(
        project_id=project_id,
        username=body.username,
        password=body.password,
        created_by=current_user.id,
    )
    await db.commit()
    return _build_response(session)


@router.post(
    "/{project_id}/google-oauth",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def capture_google_oauth_session(
    project_id: int,
    body: GoogleOAuthRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Launch a visible Chromium browser so the user can manually sign in to
    Google. Once signed in, close the browser and the storage state (cookies,
    localStorage) is encrypted and saved for future automated runs.

    The browser opens on the server machine — meant for local / Electron use.
    """
    from features.functional.core.browser.playwright_runner import PlaywrightRunner

    runner = PlaywrightRunner(headless=False)
    try:
        await runner.start()

        # Navigate to the target app's login page
        await runner.navigate(body.login_url)

        # Poll every 3 seconds for up to 3 minutes, waiting for the user to
        # finish signing in. We detect "done" when the URL changes away from
        # the Google accounts domain (or the login URL).
        max_wait_seconds = 180
        poll_interval = 3
        elapsed = 0
        logger.info("[GoogleOAuth] Waiting for user to complete sign-in...")

        while elapsed < max_wait_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            current_url = await runner.get_current_url()
            # User navigated away from login/Google → they signed in
            is_google = "accounts.google.com" in current_url
            is_login_page = current_url.rstrip("/") == body.login_url.rstrip("/")
            if not is_google and not is_login_page:
                logger.info(f"[GoogleOAuth] Sign-in detected — URL: {current_url}")
                break
        else:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Google sign-in timed out after 3 minutes. Please try again.",
            )

        # Small extra wait for page to fully settle
        await asyncio.sleep(2)

        # Capture the full storage state
        storage_state = await runner.save_storage_state()
        logger.info(f"[GoogleOAuth] Captured storage state with {len(storage_state.get('cookies', []))} cookies")

    finally:
        await runner.close()

    # Encrypt and persist
    svc = AuthSessionService(db)
    session = await svc.save_oauth_state(
        project_id=project_id,
        storage_state=storage_state,
        created_by=current_user.id,
    )
    await db.commit()
    return _build_response(session)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_auth_session(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove (deactivate) all saved auth sessions for a project."""
    svc = AuthSessionService(db)
    await svc.delete_session(project_id)
    await db.commit()
