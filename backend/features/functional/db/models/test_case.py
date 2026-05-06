"""
Test Case Model
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
import enum

from common.db.base import BaseModel


class TestCasePriority(str, enum.Enum):
    """Test case priority levels."""
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class TestCaseCategory(str, enum.Enum):
    """Test case categories."""
    smoke = "smoke"
    regression = "regression"
    e2e = "e2e"
    integration = "integration"
    sanity = "sanity"


class TestCaseStatus(str, enum.Enum):
    """Test case status."""
    draft = "draft"
    ready = "ready"
    deprecated = "deprecated"


class TestCaseSource(str, enum.Enum):
    """How the test case was authored (UI / import vs LLM)."""

    manual = "manual"
    ai = "ai"
    csv = "csv"


class TestCase(BaseModel):
    """Test case model."""
    
    __tablename__ = "test_cases"
    __table_args__ = (
        UniqueConstraint("project_id", "case_number", name="uq_test_cases_project_case_number"),
    )

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    #: Per-project sequence (1, 2, 3 …); stable display number independent of primary key.
    case_number = Column(Integer, nullable=False)
    requirement_id = Column(Integer, ForeignKey("requirements.id"), nullable=True)
    user_story_id = Column(Integer, ForeignKey("user_stories.id"), nullable=True)
    
    # Test case details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    preconditions = Column(Text, nullable=True)
    
    # Classification
    priority = Column(Enum(TestCasePriority), default=TestCasePriority.medium)
    category = Column(Enum(TestCaseCategory), default=TestCaseCategory.regression)
    status = Column(Enum(TestCaseStatus), default=TestCaseStatus.draft)
    
    # Metadata
    tags = Column(String(500), nullable=True)  # Comma-separated tags
    is_automated = Column(Boolean, default=True)
    integrity_check = Column(Boolean, default=False)  # Flag for integrity check execution
    
    # LLM generation info
    is_generated = Column(Boolean, default=False)
    generation_prompt = Column(Text, nullable=True)
    #: manual = UI; ai = LLM; csv = bulk import
    source = Column(
        Enum(TestCaseSource, native_enum=False, length=16),
        default=TestCaseSource.manual,
        nullable=False,
    )
    
    # Created by
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # External references
    jira_key = Column(String(50), nullable=True)
    azure_devops_id = Column(Integer, nullable=True)
    
    # Relationships
    requirement = relationship("Requirement", back_populates="test_cases")
    user_story = relationship("UserStory", backref="test_cases")
    steps = relationship(
        "TestStep",
        back_populates="test_case",
        order_by="TestStep.step_number",
        cascade="all, delete-orphan",
    )
    test_results = relationship("TestResult", back_populates="test_case")
    
    @property
    def steps_count(self) -> int:
        """Return the number of steps in this test case."""
        return len(self.steps) if self.steps else 0
    
    def __repr__(self):
        return f"<TestCase(id={self.id}, title='{self.title}')>"
