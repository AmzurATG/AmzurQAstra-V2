"""
GenerationJob Model — tracks async bulk test-case generation progress.
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON

from common.db.base import BaseModel


class GenerationJobStatus:
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class GenerationJobProfile:
    light = "light"        # ~5 cases per story
    standard = "standard"  # ~10 cases per story
    comprehensive = "comprehensive"  # ~20 cases per story
    production_web = "production_web"  # comprehensive + UI inventory rows


class GenerationJob(BaseModel):
    """
    Tracks a bulk test-case generation request across multiple user stories.

    One job = one batch submitted by a user. Progress is polled via GET endpoint.
    """

    __tablename__ = "generation_jobs"

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Job lifecycle
    status = Column(String(20), nullable=False, default=GenerationJobStatus.queued)
    profile = Column(String(20), nullable=False, default=GenerationJobProfile.standard)

    # Input: JSON list of user story IDs
    story_ids = Column(JSON, nullable=False, default=list)

    # Progress tracking
    total_stories = Column(Integer, nullable=False, default=0)
    completed_stories = Column(Integer, nullable=False, default=0)
    current_story_title = Column(String(500), nullable=True)

    # Output: coverage summary per story stored as JSON after completion
    coverage_report_json = Column(JSON, nullable=True)

    # Error info for failed jobs
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<GenerationJob(id={self.id}, status={self.status}, "
            f"project={self.project_id}, stories={self.total_stories})>"
        )
