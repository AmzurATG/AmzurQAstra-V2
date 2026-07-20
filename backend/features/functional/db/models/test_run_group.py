"""Test run execution group (LangGraph planner output)."""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum

from common.db.base import BaseModel


class TestRunGroupStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TestRunGroup(BaseModel):
    __tablename__ = "test_run_groups"

    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False, index=True)
    group_id = Column(String(64), nullable=False)
    title = Column(String(500), nullable=True)
    phase_order = Column(JSONB, nullable=True)
    case_ids = Column(JSONB, nullable=False, default=list)
    case_phases = Column(JSONB, nullable=True)
    merged_steps = Column(JSONB, nullable=True)
    shared_login = Column(Boolean, default=False)
    lane_id = Column(Integer, nullable=True)
    status = Column(
        Enum(TestRunGroupStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=TestRunGroupStatus.pending,
    )

    test_run = relationship("TestRun", back_populates="run_groups")

    def __repr__(self):
        return f"<TestRunGroup(run={self.test_run_id}, group={self.group_id})>"
