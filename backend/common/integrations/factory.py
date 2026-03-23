"""
Integration Factory

Factory pattern implementation for creating integration instances.
Provides a centralized registry of available integrations.
"""

from typing import Type, Dict, List, Optional

from .base import BaseIntegration, ProjectManagementIntegration, CommunicationIntegration
from .exceptions import IntegrationNotFoundError

# Import all integration implementations
from .jira.client import JiraIntegration
from .redmine.client import RedmineIntegration
from .azure_devops.client import AzureDevOpsIntegration
from .slack.client import SlackIntegration


# Registry of all available integrations
INTEGRATIONS: Dict[str, Type[BaseIntegration]] = {
    "jira": JiraIntegration,
    "redmine": RedmineIntegration,
    "azure_devops": AzureDevOpsIntegration,
    "slack": SlackIntegration,
}

# Integration metadata for frontend
INTEGRATION_METADATA = {
    "jira": {
        "type": "jira",
        "name": "Jira",
        "category": "project_management",
        "icon": "🎫",
        "description": "Import user stories and sync test results to Jira Cloud or Server",
        "features": ["Import Stories", "Import Bugs", "Sync Test Results", "Add Comments"],
    },
    "redmine": {
        "type": "redmine",
        "name": "Redmine",
        "category": "project_management",
        "icon": "🔴",
        "description": "Import issues from Redmine and sync test results",
        "features": ["Import Issues", "Sync Test Results", "Add Notes"],
    },
    "azure_devops": {
        "type": "azure_devops",
        "name": "Azure DevOps",
        "category": "project_management",
        "icon": "🔷",
        "description": "Import work items from Azure DevOps and sync test results",
        "features": ["Import User Stories", "Import Bugs", "Sync Test Results", "Add Comments"],
    },
    "slack": {
        "type": "slack",
        "name": "Slack",
        "category": "communication",
        "icon": "💬",
        "description": "Send test run notifications to Slack channels",
        "features": ["Test Run Notifications", "Failure Alerts"],
    },
}


def get_integration(integration_type: str, config: dict) -> BaseIntegration:
    """
    Factory method to create an integration instance.
    
    Args:
        integration_type: The type of integration (e.g., 'jira', 'slack')
        config: Configuration dictionary for the integration
        
    Returns:
        An instance of the appropriate integration class
        
    Raises:
        IntegrationNotFoundError: If the integration type is not registered
    """
    if integration_type not in INTEGRATIONS:
        raise IntegrationNotFoundError(
            f"Unknown integration type: {integration_type}. "
            f"Available types: {list(INTEGRATIONS.keys())}",
            integration_type=integration_type
        )
    
    integration_class = INTEGRATIONS[integration_type]
    return integration_class(config)


def get_pm_integration(integration_type: str, config: dict) -> ProjectManagementIntegration:
    """
    Get a project management integration specifically.
    
    Raises:
        IntegrationNotFoundError: If not a PM integration
    """
    integration = get_integration(integration_type, config)
    if not isinstance(integration, ProjectManagementIntegration):
        raise IntegrationNotFoundError(
            f"'{integration_type}' is not a project management integration",
            integration_type=integration_type
        )
    return integration


def get_communication_integration(integration_type: str, config: dict) -> CommunicationIntegration:
    """
    Get a communication integration specifically.
    
    Raises:
        IntegrationNotFoundError: If not a communication integration
    """
    integration = get_integration(integration_type, config)
    if not isinstance(integration, CommunicationIntegration):
        raise IntegrationNotFoundError(
            f"'{integration_type}' is not a communication integration",
            integration_type=integration_type
        )
    return integration


def get_available_integrations(category: Optional[str] = None) -> List[dict]:
    """
    Get list of available integrations with metadata.
    
    Args:
        category: Optional filter by category (e.g., 'project_management')
        
    Returns:
        List of integration metadata dictionaries
    """
    result = []
    for integration_type, cls in INTEGRATIONS.items():
        if category and cls.category != category:
            continue
        
        metadata = INTEGRATION_METADATA.get(integration_type, {})
        result.append({
            "type": integration_type,
            "name": cls.display_name,
            "category": cls.category,
            "icon": cls.icon,
            "description": metadata.get("description", ""),
            "features": metadata.get("features", []),
            "config_fields": cls.get_config_fields(),
        })
    
    return result


def get_integration_config_schema(integration_type: str) -> dict:
    """
    Get the JSON schema for an integration's configuration.
    
    Args:
        integration_type: The type of integration
        
    Returns:
        JSON schema dictionary
    """
    if integration_type not in INTEGRATIONS:
        raise IntegrationNotFoundError(
            f"Unknown integration type: {integration_type}",
            integration_type=integration_type
        )
    
    cls = INTEGRATIONS[integration_type]
    return cls.get_config_schema().model_json_schema()


def register_integration(integration_type: str, cls: Type[BaseIntegration]) -> None:
    """
    Register a new integration type at runtime.
    
    Useful for plugins or dynamic integration loading.
    
    Args:
        integration_type: Unique identifier for the integration
        cls: The integration class to register
    """
    INTEGRATIONS[integration_type] = cls
