"""Typed HTTP request and response models for the local Dashboard."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Reject accidental fields at the HTTP seam."""

    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    """Dashboard health response."""

    ok: bool
    version: str


class BootstrapResponse(StrictModel):
    """Small payload used to select the initial Dashboard state."""

    version: str
    workspace_count: int
    has_workspaces: bool


class RegisterWorkspaceRequest(StrictModel):
    """Request to add an already initialized Workspace."""

    path: str = Field(min_length=1)


class WorkspaceFolderSelectionResponse(StrictModel):
    """Result of opening the local native Workspace folder selector."""

    path: Path | None
    cancelled: bool


class InitializeWorkspaceRequest(StrictModel):
    """Request to create a Workspace through the existing initializer."""

    path: str = Field(min_length=1)
    name: str | None = None
    repositories: list[str] = Field(default_factory=list)


class WorkspaceResponse(StrictModel):
    """A registered Workspace and its filesystem health."""

    workspace_id: UUID
    name: str
    path: Path
    registered_at: str
    health: str
    detail: str


class RepositoryOverviewResponse(StrictModel):
    """Safe Repository metadata for the overview page."""

    name: str
    path: Path
    branch: str
    revision: str
    health: str
    detail: str


class WorkspaceOverviewResponse(StrictModel):
    """Workspace identity and Repository health."""

    workspace_id: UUID
    name: str
    path: Path
    created_at: str
    lumon_version: str
    repositories: list[RepositoryOverviewResponse]


class FeishuWebhookResponse(StrictModel):
    """Display-safe Feishu Webhook settings."""

    enabled: bool
    configured: bool
    masked_url: str | None


class WorkspaceSettingsResponse(StrictModel):
    """Display-safe Workspace settings."""

    workspace_id: UUID
    feishu_webhook: FeishuWebhookResponse


class FeishuWebhookUpdate(StrictModel):
    """Partial update for Feishu Webhook settings."""

    enabled: bool
    url: str | None = None


class WorkspaceSettingsUpdate(StrictModel):
    """Typed settings update without a generic key-value escape hatch."""

    feishu_webhook: FeishuWebhookUpdate


class FeishuWebhookTestRequest(StrictModel):
    """Optional draft URL for a non-persisting Webhook test."""

    url: str | None = None


class RepositoryResultResponse(StrictModel):
    """One Repository outcome returned by initialization."""

    name: str
    path: Path
    status: str
    branch: str | None
    revision: str | None


class InitializeWorkspaceResponse(StrictModel):
    """Initialization outcome plus its new registry identity."""

    status: str
    workspace: Path
    workspace_id: UUID
    repositories: list[RepositoryResultResponse]


class WebhookTestResponse(StrictModel):
    """Safe result of a Feishu Webhook test."""

    success: bool
    detail: str
