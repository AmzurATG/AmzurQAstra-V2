"""
QAstra Integration System

Strategy Pattern + Factory Pattern implementation for external integrations.
Supports: Jira, Redmine, Azure DevOps, Slack, Confluence, GitHub
"""

from .base import (
    BaseIntegration,
    BaseIntegrationConfig,
    ProjectManagementIntegration,
    CommunicationIntegration,
    DocumentationIntegration,
    UserStoryData,
    ProjectData,
    TestResultData,
)
from .factory import get_integration, get_available_integrations, INTEGRATIONS
from .exceptions import (
    IntegrationError,
    IntegrationConnectionError,
    IntegrationAuthError,
    IntegrationSyncError,
    IntegrationNotFoundError,
    IntegrationConfigError,
)

__all__ = [
    # Base classes
    "BaseIntegration",
    "BaseIntegrationConfig",
    "ProjectManagementIntegration",
    "CommunicationIntegration",
    "DocumentationIntegration",
    # Data models
    "UserStoryData",
    "ProjectData",
    "TestResultData",
    # Factory
    "get_integration",
    "get_available_integrations",
    "INTEGRATIONS",
    # Exceptions
    "IntegrationError",
    "IntegrationConnectionError",
    "IntegrationAuthError",
    "IntegrationSyncError",
    "IntegrationNotFoundError",
    "IntegrationConfigError",
]
