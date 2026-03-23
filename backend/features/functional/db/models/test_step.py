"""
Test Step Model
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from common.db.base import BaseModel


class TestStepAction(str, enum.Enum):
    """Test step action types."""
    navigate = "navigate"
    click = "click"
    type = "type"
    fill = "fill"
    select = "select"
    check = "check"
    uncheck = "uncheck"
    hover = "hover"
    screenshot = "screenshot"
    wait = "wait"
    assert_text = "assert_text"
    assert_visible = "assert_visible"
    assert_url = "assert_url"
    assert_title = "assert_title"
    custom = "custom"


class TestStep(BaseModel):
    """Test step model."""
    
    __tablename__ = "test_steps"
    
    test_case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False)
    
    # Step details
    step_number = Column(Integer, nullable=False)
    action = Column(Enum(TestStepAction), nullable=False)
    target = Column(String(500), nullable=True)  # Selector or URL
    value = Column(Text, nullable=True)  # Input value or expected text
    
    # Description
    description = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=True)
    
    # Generated Playwright code
    playwright_code = Column(Text, nullable=True)
    
    # Selector strategy (for generated selectors)
    selector_type = Column(String(50), nullable=True)  # css, xpath, text, role
    selector_confidence = Column(Integer, nullable=True)  # 0-100
    
    # Relationships
    test_case = relationship("TestCase", back_populates="steps")
    
    def __repr__(self):
        return f"<TestStep(id={self.id}, action='{self.action}', step={self.step_number})>"
