"""Pydantic schemas for UI Discovery API and inventory contract."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class UiElement(BaseModel):
    type: str = Field(..., description="input | button | link | select | checkbox | text | other")
    label: str = ""
    placeholder: Optional[str] = None
    name: Optional[str] = None


class UiPage(BaseModel):
    name: str
    url: str = ""
    elements: List[UiElement] = Field(default_factory=list)
    tabs: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None


class UiInventory(BaseModel):
    """Contract for downstream generation prompts."""

    platform: Literal["web"] = "web"
    actor_role: str = "end_user"
    app_url: str
    discovered_at: str
    pages: List[UiPage] = Field(default_factory=list)
    navigation: List[str] = Field(default_factory=list)
    modules_inferred: List[str] = Field(default_factory=list)


class UiDiscoveryCredentials(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class UiDiscoveryStartRequest(BaseModel):
    project_id: int
    app_url: str
    actor_role: str = Field(default="end_user", description="end_user | support_admin | ops_admin | super_admin")
    credentials: Optional[UiDiscoveryCredentials] = None
    use_google_signin: bool = False
    skip_reachability_check: bool = False
    source_integrity_run_id: Optional[int] = None


class UiDiscoveryStartResponse(BaseModel):
    run_id: str
    status: str = "pending"


class UiDiscoveryStatusResponse(BaseModel):
    run_id: str
    status: str
    percentage: int = 0
    current_step: Optional[str] = None
    platform: str = "web"
    actor_role: str = "end_user"
    app_url: str
    inventory: Optional[UiInventory] = None
    partial_inventory: Optional[Dict[str, Any]] = None
    screenshots: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    pages_discovered: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class UiDiscoveryHistoryItem(BaseModel):
    id: int
    run_id: str
    status: str
    platform: str
    actor_role: str
    app_url: str
    pages_discovered: int = 0
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class UiDiscoveryLatestResponse(BaseModel):
    found: bool
    run_id: Optional[str] = None
    inventory: Optional[UiInventory] = None
    discovered_at: Optional[str] = None
    is_stale: bool = False
    days_since_discovery: Optional[int] = None
