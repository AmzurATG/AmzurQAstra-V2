"""
Auth Session Service

Manages encrypted browser auth sessions per project.
Credentials and Playwright storageState (OAuth) are encrypted at rest
using Fernet symmetric encryption with the project's ENCRYPTION_KEY.
"""
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from cryptography.fernet import Fernet
from common.db.models.auth_session import AuthSession
from config import settings
from common.utils.logger import logger


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured ENCRYPTION_KEY."""
    key = settings.ENCRYPTION_KEY
    # Fernet requires a 32-byte URL-safe base64 key — pad/truncate if needed
    key_bytes = key.encode()[:32].ljust(32, b"=")
    import base64
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def _encrypt(data: str) -> str:
    return _get_fernet().encrypt(data.encode()).decode()


def _decrypt(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


class AuthSessionService:
    """CRUD service for project auth sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_session(self, project_id: int) -> Optional[AuthSession]:
        """Return the most recently created active session for a project."""
        result = await self.db.execute(
            select(AuthSession)
            .where(AuthSession.project_id == project_id)
            .where(AuthSession.is_active == True)
            .order_by(AuthSession.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_credentials(
        self,
        project_id: int,
        username: str,
        password: str,
        created_by: Optional[int] = None,
    ) -> AuthSession:
        """Encrypt and persist username/password credentials for a project."""
        # Deactivate existing sessions first
        await self._deactivate_all(project_id)

        payload = json.dumps({"username": username, "password": password})
        session = AuthSession(
            project_id=project_id,
            created_by=created_by,
            auth_type="credentials",
            encrypted_credentials=_encrypt(payload),
            is_active=True,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        logger.info(f"[AuthSession] Saved credentials session for project {project_id}")
        return session

    async def save_oauth_state(
        self,
        project_id: int,
        storage_state: dict,
        created_by: Optional[int] = None,
    ) -> AuthSession:
        """Encrypt and persist a Playwright storageState dict (Google OAuth)."""
        await self._deactivate_all(project_id)

        session = AuthSession(
            project_id=project_id,
            created_by=created_by,
            auth_type="google_oauth",
            encrypted_storage_state=_encrypt(json.dumps(storage_state)),
            is_active=True,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        logger.info(f"[AuthSession] Saved OAuth session for project {project_id}")
        return session

    def decrypt_credentials(self, session: AuthSession) -> Optional[dict]:
        """Decrypt and return {username, password} dict from a credentials session."""
        if not session.encrypted_credentials:
            return None
        try:
            return json.loads(_decrypt(session.encrypted_credentials))
        except Exception as e:
            logger.error(f"[AuthSession] Failed to decrypt credentials: {e}")
            return None

    def decrypt_storage_state(self, session: AuthSession) -> Optional[dict]:
        """Decrypt and return the Playwright storageState dict."""
        if not session.encrypted_storage_state:
            return None
        try:
            return json.loads(_decrypt(session.encrypted_storage_state))
        except Exception as e:
            logger.error(f"[AuthSession] Failed to decrypt storage state: {e}")
            return None

    async def delete_session(self, project_id: int) -> bool:
        """Deactivate all sessions for a project."""
        await self._deactivate_all(project_id)
        return True

    async def _deactivate_all(self, project_id: int) -> None:
        """Mark all existing sessions for a project as inactive."""
        result = await self.db.execute(
            select(AuthSession)
            .where(AuthSession.project_id == project_id)
            .where(AuthSession.is_active == True)
        )
        for session in result.scalars().all():
            session.is_active = False
        await self.db.flush()
