"""
Security Question Model

Stores security questions and bcrypt-hashed answers for each user.
Used for password recovery verification.
"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from common.db.base import BaseModel


class SecurityQuestion(BaseModel):
    """Security question with hashed answer, linked to a user."""

    __tablename__ = "security_questions"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(String(500), nullable=False)
    answer_hash = Column(String(255), nullable=False)  # bcrypt hashed (case-insensitive)

    # Relationship
    user = relationship("User", backref="security_questions")

    def __repr__(self):
        return f"<SecurityQuestion(id={self.id}, user_id={self.user_id})>"
