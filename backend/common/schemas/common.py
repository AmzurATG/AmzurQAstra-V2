"""
Common Schemas
"""
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel
from enum import Enum


T = TypeVar("T")


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class FilterParams(BaseModel):
    """Common filter parameters."""
    search: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.DESC
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class DateRangeFilter(BaseModel):
    """Date range filter."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class BulkActionRequest(BaseModel):
    """Bulk action request."""
    ids: List[int]


class BulkActionResponse(BaseModel):
    """Bulk action response."""
    success_count: int
    failed_count: int
    failed_ids: List[int] = []
    message: str
