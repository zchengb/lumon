"""Typed HTTP request and response models for the local Dashboard."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from lumon.agents.agent.config import AGENT_REASONING_EFFORT_PATTERN
from lumon.delivery.model import DeliveryPollState, DeliveryState
from lumon.tools.codex_status import CodexCliUpdateStatus
from lumon.workspace.settings import DeliveryPublishMode


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


class AgentModelResponse(StrictModel):
    """Model metadata exposed by the local Codex catalog."""

    model: str
    display_name: str
    description: str
    default_reasoning_effort: str
    supported_reasoning_efforts: list[str]


class CodexCliStatusResponse(StrictModel):
    """Read-only update metadata for Lumon's active Codex CLI."""

    status: CodexCliUpdateStatus
    binary_path: str
    installed_version: str | None
    latest_version: str | None


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
    agent_reasoning_effort: str = Field(pattern=AGENT_REASONING_EFFORT_PATTERN, max_length=32)
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


class WorkflowScheduleResponse(StrictModel):
    """Display-safe saved workflow schedule for the Overview automation panel."""

    flow_id: str
    name: str
    enabled: bool
    schedule_expression: str


class WorkspaceOverviewResponse(StrictModel):
    """Workspace identity, Repository health and saved workflow schedules."""

    workspace_id: UUID
    name: str
    path: Path
    created_at: str
    lumon_version: str
    repositories: list[RepositoryOverviewResponse]
    workflow_schedules: list[WorkflowScheduleResponse] = Field(
        default_factory=list[WorkflowScheduleResponse]
    )


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
    jira_site: str
    trigger_jql: str
    publish_mode: DeliveryPublishMode
    target_branch: str


class DeliveryRunResponse(StrictModel):
    """A safe Story receipt with human-readable timing in the client."""

    run_id: str
    story_key: str
    story_title: str
    state: DeliveryState
    phase: str
    started_at: datetime
    finished_at: datetime | None
    jira_url: str | None
    repository: str | None
    branch: str | None
    pull_request_url: str | None
    verification_summary: str | None
    detail: str | None
    reason: str | None
    poll_id: str | None
    duration_seconds: int | None


class DeliveryPollResponse(StrictModel):
    run_id: str
    state: DeliveryPollState
    phase: str
    started_at: datetime
    finished_at: datetime | None
    detail: str
    duration_seconds: int | None


class DeliveryHistoryResponse(StrictModel):
    runs: list[DeliveryRunResponse]
    polls: list[DeliveryPollResponse]


class DeliveryActivityResponse(StrictModel):
    at: datetime
    phase: str
    detail: str


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
    jira_site: str | None = Field(default=None, max_length=253)
    trigger_jql: str | None = Field(default=None, max_length=8_000)
    publish_mode: DeliveryPublishMode | None = None
    target_branch: str | None = Field(default=None, max_length=256)


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
