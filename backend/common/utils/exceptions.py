"""
Custom Exceptions
"""
from typing import Optional, Any


class QAstraException(Exception):
    """Base exception for QAstra."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Any] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class NotFoundError(QAstraException):
    """Resource not found error."""
    
    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} with ID {resource_id} not found",
            error_code="NOT_FOUND",
        )


class ValidationError(QAstraException):
    """Validation error."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(QAstraException):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, error_code="AUTH_ERROR")


class AuthorizationError(QAstraException):
    """Authorization error."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message=message, error_code="PERMISSION_DENIED")


class IntegrationError(QAstraException):
    """External integration error."""
    
    def __init__(self, integration: str, message: str):
        super().__init__(
            message=f"{integration} integration error: {message}",
            error_code="INTEGRATION_ERROR",
        )


class LLMError(QAstraException):
    """LLM API error."""
    
    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(
            message=f"LLM error: {message}",
            error_code="LLM_ERROR",
            details={"provider": provider},
        )


class MCPError(QAstraException):
    """MCP Server error."""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"MCP server error: {message}",
            error_code="MCP_ERROR",
        )


class TestExecutionError(QAstraException):
    """Test execution error."""
    
    def __init__(self, message: str, test_case_id: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="TEST_EXECUTION_ERROR",
            details={"test_case_id": test_case_id},
        )
