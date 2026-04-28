"""
Test recommendation run: domain-based test strategy suggestions from BRD + user stories.

Persisted in PostgreSQL as table ``test_recommendation_runs`` (see migration). Each row is one
execution: ``result_json`` holds the playbook output (domain, standard_tests, recommended_tests,
warnings, etc.); ``status`` is completed | failed; failures store ``error_message``.
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from common.db.base import BaseModel


class TestRecommendationRun(BaseModel):
    """One test recommendation execution for a requirement within a project."""

    __tablename__ = "test_recommendation_runs"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(20), nullable=False, default="pending")  # pending | completed | failed
    result_json = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)

    requirement = relationship("Requirement", backref="test_recommendation_runs")

    def __repr__(self) -> str:
        return f"<TestRecommendationRun(id={self.id}, status={self.status!r})>"
