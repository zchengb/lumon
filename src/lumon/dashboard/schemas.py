"""Typed HTTP request and response models for the local Dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
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


class AgentObservabilityResponse(StrictModel):
    """Display-safe Langfuse settings for the global Agent."""

    enabled: bool
    provider: str
    base_url: str
    sample_rate: float
    public_key_configured: bool
    secret_key_configured: bool
    public_key_masked: str | None
    secret_key_masked: str | None


class AgentSettingsResponse(StrictModel):
    """Display-safe global Agent settings."""

    enabled: bool
    default_workspace_id: UUID | None
    agent_provider: str
    agent_model: str
    agent_reasoning_effort: str
    feishu_app_id: str
    feishu_app_configured: bool
    feishu_app_secret_masked: str | None
    observability: AgentObservabilityResponse


class AgentObservabilityUpdate(StrictModel):
    """Langfuse settings with optional credential replacements."""

    enabled: bool
    base_url: str = Field(min_length=1)
    sample_rate: float = Field(ge=0.0, le=1.0)
    public_key: str | None = None
    secret_key: str | None = None
    clear_credentials: bool = False


class AgentSettingsUpdate(StrictModel):
    """Global Agent settings submitted by the Dashboard."""

    enabled: bool
    default_workspace_id: UUID | None
    agent_model: str = Field(min_length=1)
    agent_reasoning_effort: Literal["minimal", "low", "medium", "high", "xhigh", "max", "ultra"]
    feishu_app_id: str = Field(min_length=1)
    feishu_app_secret: str | None = None
    observability: AgentObservabilityUpdate


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


class AutoDeliveryResponse(StrictModel):
    """Display-safe Auto Delivery settings."""

    enabled: bool
    trigger_hooks: list[str]
    schedule_expression: str


class AutoScanResponse(StrictModel):
    """Display-safe Auto Scan settings."""

    enabled: bool
    lookback_days: int
    trigger_hooks: list[str]
    schedule_expression: str
    workflow_description: str


class WorkspaceSettingsResponse(StrictModel):
    """Display-safe Workspace settings."""

    workspace_id: UUID
    feishu_webhook: FeishuWebhookResponse
    auto_delivery: AutoDeliveryResponse
    auto_scan: AutoScanResponse


class FeishuWebhookUpdate(StrictModel):
    """Partial update for Feishu Webhook settings."""

    enabled: bool
    url: str | None = None


class AutoDeliveryUpdate(StrictModel):
    """Workspace Auto Delivery permission update."""

    enabled: bool
    trigger_hooks: list[str] | None = None
    schedule_expression: str | None = None


class AutoScanUpdate(StrictModel):
    """Workspace Auto Scan configuration update."""

    enabled: bool
    lookback_days: int = Field(ge=1, le=365)
    trigger_hooks: list[str] | None = None
    schedule_expression: str | None = None
    workflow_description: str | None = Field(default=None, max_length=8_000)


class WorkspaceSettingsUpdate(StrictModel):
    """Typed settings update without a generic key-value escape hatch."""

    feishu_webhook: FeishuWebhookUpdate
    auto_delivery: AutoDeliveryUpdate | None = None
    auto_scan: AutoScanUpdate | None = None


class ScanFindingResponse(StrictModel):
    """One safe finding returned in Auto Scan history."""

    title: str
    severity: str
    repository: str
    impact: str
    trigger: str
    file: str
    line_range: str
    code_snippet: str
    suggestion: str
    root_cause: str
    validation: str
    issue_id: str
    issue_status: str
    pr_url: str | None


class ScanRunResponse(StrictModel):
    """One Auto Scan history row."""

    run_id: str
    state: str
    phase: str
    started_at: str
    finished_at: str | None
    lookback_days: int
    repositories_scanned: int
    repositories_failed: int
    findings: list[ScanFindingResponse]
    failures: list[str]
    hook_results: list[str]
    html_available: bool
    pdf_available: bool
    duration_seconds: int | None


class FlowSummaryResponse(StrictModel):
    """Display-safe metadata for one Workspace flow."""

    flow_id: str
    name: str
    enabled: bool
    brief: str
    path: str
    valid: bool
    error: str | None = None


class FlowDocumentResponse(FlowSummaryResponse):
    """One flow document returned to the Dashboard editor."""

    content: str
    schedule_enabled: bool
    schedule_expression: str


class FlowContentRequest(StrictModel):
    """Markdown content submitted for flow creation or replacement."""

    content: str = Field(min_length=1)


class FlowScheduleUpdate(StrictModel):
    """Machine-local schedule for one exact Flow."""

    enabled: bool
    schedule_expression: str = Field(min_length=1, max_length=128)


class CapabilitySummaryResponse(StrictModel):
    """Display-safe metadata for one Workspace capability."""

    capability_id: str
    name: str
    enabled: bool
    brief: str
    path: str
    valid: bool
    error: str | None = None


class CapabilityDocumentResponse(CapabilitySummaryResponse):
    """One capability document returned to the Dashboard editor."""

    content: str


class CapabilityContentRequest(StrictModel):
    """Markdown content submitted for capability creation or replacement."""

    content: str = Field(min_length=1)


class FeishuWebhookTestRequest(StrictModel):
    """Optional draft URL for a non-persisting Webhook test."""

    url: str | None = None


class RepositoryResultResponse(StrictModel):
    """One Repository outcome returned by initialization."""

    name: str
    path: Path
    status: str
    branch: str | None


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
