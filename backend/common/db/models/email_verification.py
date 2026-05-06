"""
Email Verification Model

Stores pending OTP verifications for the signup flow.
Each row represents an in-progress signup that hasn't been verified yet.
"""
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB

from common.db.base import BaseModel


class EmailVerification(BaseModel):
    """Tracks OTP-based email verification during signup."""

    __tablename__ = "email_verifications"

    email = Column(String(255), unique=True, nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    user_data = Column(JSONB, nullable=False)  # Pending registration data
    security_questions = Column(JSONB, nullable=True)  # Q&A pairs (answers hashed)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EmailVerification(id={self.id}, email='{self.email}')>"
