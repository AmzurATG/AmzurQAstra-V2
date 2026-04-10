"""
Gap analysis run: compares BRD (requirement) text to project user stories via LLM.
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from common.db.base import BaseModel


class GapAnalysisRun(BaseModel):
    """One gap analysis execution for a requirement (BRD) within a project."""

    __tablename__ = "gap_analysis_runs"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String(20), nullable=False, default="pending")  # pending | completed | failed
    result_json = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)

    requirement = relationship("Requirement", backref="gap_analysis_runs")

    def __repr__(self) -> str:
        return f"<GapAnalysisRun(id={self.id}, status={self.status!r})>"
