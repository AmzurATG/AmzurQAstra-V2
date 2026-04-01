"""
Integrity Check Result DB Model
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from common.db.base import BaseModel


class IntegrityCheckResult(BaseModel):
    """Stores each integrity check run — both live (status/progress) and historical."""

    __tablename__ = "integrity_check_results"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)

    # Lifecycle: pending → running → completed | error
    status = Column(String(20), default="pending", nullable=False)
    app_url = Column(String(500), nullable=False)

    # Outcome
    app_reachable = Column(Boolean, nullable=True)
    login_successful = Column(Boolean, nullable=True)
    overall_status = Column(String(20), nullable=True)  # passed | failed | error

    # Step counts
    steps_total = Column(Integer, default=0)
    steps_passed = Column(Integer, default=0)
    steps_failed = Column(Integer, default=0)

    # Agent narrative output
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Structured results stored as JSON
    steps_data = Column(JSONB, nullable=True)       # list[{step_number, description, screenshot_path}]
    screenshots = Column(JSONB, nullable=True)      # list[str] — /screenshots/<filename>

    # Timing
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<IntegrityCheckResult(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"
