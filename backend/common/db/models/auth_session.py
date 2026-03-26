"""
Auth Session Model

Stores encrypted browser credentials and OAuth storage state per project.
Used by IntegrityCheck and test execution to replay authenticated sessions
without re-entering credentials on every run.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from common.db.base import BaseModel


class AuthSession(BaseModel):
    """Encrypted auth session per project."""

    __tablename__ = "auth_sessions"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # 'credentials' = username/password login
    # 'google_oauth' = OAuth storage state replay (future)
    auth_type = Column(String(30), nullable=False, default="credentials")

    # Fernet-encrypted JSON: {"username": "...", "password": "..."}
    encrypted_credentials = Column(Text, nullable=True)

    # Fernet-encrypted Playwright storageState JSON for Google OAuth session replay
    encrypted_storage_state = Column(Text, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    project = relationship("Project", foreign_keys=[project_id])

    def __repr__(self):
        return f"<AuthSession(id={self.id}, project_id={self.project_id}, type={self.auth_type})>"
