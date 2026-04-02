"""
Test Result Model
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from common.db.base import BaseModel


class TestResultStatus(str, enum.Enum):
    """Test result status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class TestResult(BaseModel):
    """Test result model - individual test case result in a test run."""
    
    __tablename__ = "test_results"
    
    test_run_id = Column(Integer, ForeignKey("test_runs.id"), nullable=False)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    
    # Result
    status = Column(Enum(TestResultStatus, values_callable=lambda e: [x.value for x in e]), nullable=False)
    duration_ms = Column(Integer, nullable=True)  # Execution time in milliseconds
    
    # Failure details
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    failed_step = Column(Integer, nullable=True)  # Step number where it failed
    
    # Evidence
    screenshot_path = Column(String(500), nullable=True)
    video_path = Column(String(500), nullable=True)
    trace_path = Column(String(500), nullable=True)
    
    # Step-by-step results
    step_results = Column(JSONB, nullable=True)  # Array of step results
    adapted_steps = Column(JSONB, nullable=True)  # Array of steps that were adapted by AI
    original_steps = Column(JSONB, nullable=True)  # Array of original steps for comparison
    # Per browser-use agent iteration: timestamp, agent_step, description, adaptation, screenshot_path
    agent_logs = Column(JSONB, nullable=True)
    
    # Execution timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    test_run = relationship("TestRun", back_populates="test_results")
    test_case = relationship("TestCase", back_populates="test_results")
    
    def __repr__(self):
        return f"<TestResult(id={self.id}, status='{self.status}')>"
