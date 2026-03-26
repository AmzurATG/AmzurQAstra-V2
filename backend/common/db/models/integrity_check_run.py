"""
Integrity Check Run Models

Persists every integrity check execution and its per-step results so the
history tab in the UI can show past runs with full step-by-step detail
and LLM diagnosis for failures.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from common.db.base import BaseModel


class IntegrityCheckRun(BaseModel):
    """One integrity check run triggered by a user."""

    __tablename__ = "integrity_check_runs"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Overall result
    status = Column(String(20), nullable=False, default="pending")   # pending | running | passed | failed | error
    app_url = Column(String(500), nullable=False)
    app_reachable = Column(Boolean, nullable=True)
    login_successful = Column(Boolean, nullable=True)

    # Engine and auth choices recorded at run time
    browser_engine = Column(String(30), nullable=False, default="playwright")  # playwright | steel
    auth_method = Column(String(30), nullable=False, default="none")  # none | credentials | google_oauth | google_sso

    # Aggregated counts
    test_cases_total = Column(Integer, default=0)
    test_cases_passed = Column(Integer, default=0)
    test_cases_failed = Column(Integer, default=0)

    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)

    # Relationships
    step_results = relationship(
        "IntegrityCheckStepResult",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="IntegrityCheckStepResult.id",
    )

    def __repr__(self):
        return f"<IntegrityCheckRun(id={self.id}, project={self.project_id}, status={self.status})>"


class IntegrityCheckStepResult(BaseModel):
    """One step result within an integrity check run."""

    __tablename__ = "integrity_check_step_results"

    run_id = Column(Integer, ForeignKey("integrity_check_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=True)

    # Test case context (denormalised for easy display without joins)
    test_case_title = Column(String(500), nullable=True)
    test_case_status = Column(String(20), nullable=True)   # passed | failed | error
    test_case_duration_ms = Column(Integer, nullable=True)

    # Step detail
    step_number = Column(Integer, nullable=False)
    action = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")   # pending | passed | failed | error
    error = Column(Text, nullable=True)

    # URL path served by the /screenshots static mount
    screenshot_path = Column(String(500), nullable=True)

    # LLM failure diagnosis — only populated when status == 'failed'
    llm_diagnosis = Column(Text, nullable=True)

    duration_ms = Column(Integer, nullable=True)

    # Relationships
    run = relationship("IntegrityCheckRun", back_populates="step_results")

    def __repr__(self):
        return f"<StepResult(run={self.run_id}, step={self.step_number}, status={self.status})>"
