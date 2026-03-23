"""
Integration-specific exceptions
"""


class IntegrationError(Exception):
    """Base exception for all integration errors"""
    
    def __init__(self, message: str, integration_type: str = None):
        self.integration_type = integration_type
        super().__init__(message)


class IntegrationConnectionError(IntegrationError):
    """Failed to connect to the external service"""
    pass


class IntegrationAuthError(IntegrationError):
    """Authentication/authorization failed"""
    pass


class IntegrationSyncError(IntegrationError):
    """Failed to sync data"""
    
    def __init__(self, message: str, integration_type: str = None, failed_items: list = None):
        self.failed_items = failed_items or []
        super().__init__(message, integration_type)


class IntegrationNotFoundError(IntegrationError):
    """Integration type not registered"""
    pass


class IntegrationConfigError(IntegrationError):
    """Invalid configuration"""
    pass


class IntegrationRateLimitError(IntegrationError):
    """Rate limit exceeded"""
    
    def __init__(self, message: str, integration_type: str = None, retry_after: int = None):
        self.retry_after = retry_after
        super().__init__(message, integration_type)
