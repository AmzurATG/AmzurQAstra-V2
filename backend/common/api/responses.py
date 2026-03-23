"""
Standard API Response Models
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    
    @classmethod
    def success_response(cls, data: T = None, message: str = "Success"):
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(cls, message: str, data: Any = None):
        return cls(success=False, message=message, data=data)


class ErrorResponse(BaseModel):
    """Error response model."""
    
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
