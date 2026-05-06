"""
SQLAlchemy Base Model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func, MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

from config import settings

# Use the configured schema for all tables
_schema = settings.DB_SCHEMA


class Base(DeclarativeBase):
    """Base class for all database models."""

    metadata = MetaData(schema=_schema)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """Base model with common fields."""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
