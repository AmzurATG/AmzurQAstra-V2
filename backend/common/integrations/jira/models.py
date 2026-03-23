"""
Jira Models
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class JiraProject(BaseModel):
    """Jira project model."""
    id: str
    key: str
    name: str
    description: Optional[str] = None


class JiraSprint(BaseModel):
    """Jira sprint model."""
    id: int
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class JiraTestCase(BaseModel):
    """Test case synced from/to Jira."""
    jira_key: str
    summary: str
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    priority: Optional[str] = None
    labels: List[str] = []
    
    # QAstra mappings
    qastra_test_case_id: Optional[int] = None
    synced_at: Optional[datetime] = None
