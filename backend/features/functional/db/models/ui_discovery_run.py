"""
UI Discovery Run DB Model — stores structured page/element inventory from live app exploration.
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB

from common.db.base import BaseModel


class UiDiscoveryRunStatus:
    pending = "pending"
    running = "running"
    completed = "completed"
    error = "error"


class UiDiscoveryRun(BaseModel):
    """Stores each UI discovery run and its structured inventory."""

    __tablename__ = "ui_discovery_runs"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)

    status = Column(String(20), default=UiDiscoveryRunStatus.pending, nullable=False)
    platform = Column(String(20), default="web", nullable=False)
    actor_role = Column(String(32), default="end_user", nullable=False)

    app_url = Column(String(500), nullable=False)
    inventory_json = Column(JSONB, nullable=True)
    screenshots = Column(JSONB, nullable=True)

    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    source_integrity_run_id = Column(
        Integer,
        ForeignKey("integrity_check_results.id", ondelete="SET NULL"),
        nullable=True,
    )

    live_progress = Column(JSONB, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<UiDiscoveryRun(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"
