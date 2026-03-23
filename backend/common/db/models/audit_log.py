"""
Audit Log Model
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB

from common.db.base import BaseModel


class AuditLog(BaseModel):
    """Audit log for tracking changes."""
    
    __tablename__ = "audit_logs"
    
    # Who
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # What
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, EXECUTE
    entity_type = Column(String(100), nullable=False)  # test_case, test_run, etc.
    entity_id = Column(Integer, nullable=True)
    
    # Details
    description = Column(Text, nullable=True)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', entity='{self.entity_type}')>"
