"""
Test Run Model
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from common.db.base import BaseModel


class TestRunStatus(str, enum.Enum):
    """Test run status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


class TestRun(BaseModel):
    """Test run model."""
    
    __tablename__ = "test_runs"
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # Run details
    name = Column(String(255), nullable=True)
    description = Column(String(1000), nullable=True)
    status = Column(Enum(TestRunStatus, values_callable=lambda e: [x.value for x in e]), default=TestRunStatus.PENDING)
    
    # Execution info
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results summary
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    skipped_tests = Column(Integer, default=0)
    
    # Configuration
    browser = Column(String(50), default="chromium")
    headless = Column(String(10), default="true")
    config = Column(JSONB, nullable=True)  # Additional config
    
    # Report
    report_path = Column(String(500), nullable=True)
    
    # Relationships
    test_results = relationship(
        "TestResult",
        back_populates="test_run",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self):
        return f"<TestRun(id={self.id}, status='{self.status}')>"
