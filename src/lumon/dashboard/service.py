"""Dashboard use cases over the typed Workspace and profile modules."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal
from uuid import UUID

from lumon.agents.agent.config import (
    AgentConfig,
    AgentConfigStore,
    AgentReasoningEffort,
    ObservabilityConfig,
)
from lumon.capabilities.catalog import CapabilityCatalog, CapabilityValidationError
from lumon.capabilities.model import CapabilityDefinition
from lumon.dashboard.folder_picker import FolderPicker
from lumon.delivery.scheduler import DeliveryScheduler, LaunchdDeliveryScheduler
from lumon.errors import AgentConfigError, LumonError, PreflightError, WorkspaceNotFoundError
from lumon.flows.catalog import FlowCatalog, FlowValidationError
from lumon.flows.model import FlowDefinition
from lumon.scan.model import ScanRun
from lumon.scan.scheduler import LaunchdScanScheduler, ScanScheduler
from lumon.scan.service import ScanService
from lumon.tools.feishu_webhook import FeishuWebhookSender, WebhookTestResult, validate_webhook_url
from lumon.workspace.config import load_workspace_config
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.model import InitRequest, InitResult
from lumon.workspace.registry import WorkspaceRegistration, WorkspaceRegistry
from lumon.workspace.repositories import RepositoryProvisioner, spec_from_url
from lumon.workspace.settings import (
    AutoDeliverySettings,
    AutoScanSettings,
    FeishuWebhookSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
    masked_secret,
    masked_webhook_url,
)

WorkspaceHealth = Literal["ready", "missing", "invalid"]
RepositoryHealth = Literal["ready", "unhealthy"]


@dataclass(frozen=True, slots=True)
class WorkspaceListItem:
    """A registry entry plus the current filesystem health of its Workspace."""

    registration: WorkspaceRegistration
    health: WorkspaceHealth
    detail: str


@dataclass(frozen=True, slots=True)
class RepositoryOverview:
    """Safe Repository metadata shown in the Dashboard overview."""

    name: str
    path: Path
    branch: str
    health: RepositoryHealth
    detail: str


@dataclass(frozen=True, slots=True)
class WorkspaceOverview:
    """The read-only summary of one registered Workspace."""

    workspace_id: UUID
    name: str
    path: Path
    created_at: str
    lumon_version: str
    repositories: tuple[RepositoryOverview, ...]


@dataclass(frozen=True, slots=True)
class WebhookSettingsView:
    """A display-safe Webhook view that never contains its saved URL."""

    enabled: bool
    configured: bool
    masked_url: str | None


@dataclass(frozen=True, slots=True)
class AutoDeliverySettingsView:
    """Display-safe Auto Delivery permission for one Workspace."""

    enabled: bool
    trigger_hooks: tuple[str, ...]
    schedule_expression: str


@dataclass(frozen=True, slots=True)
class AutoScanSettingsView:
    """Display-safe Auto Scan configuration for one Workspace."""

    enabled: bool
    lookback_days: int
    trigger_hooks: tuple[str, ...]
    schedule_expression: str
    workflow_description: str


@dataclass(frozen=True, slots=True)
class WorkspaceSettingsView:
    """The display-safe settings view for one Workspace."""

    workspace_id: UUID
    feishu_webhook: WebhookSettingsView
    auto_delivery: AutoDeliverySettingsView
    auto_scan: AutoScanSettingsView


@dataclass(frozen=True, slots=True)
class FlowSummaryView:
    """Display-safe metadata for one Workspace flow."""

    flow_id: str
    name: str
    enabled: bool
    brief: str
    path: str
    valid: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class FlowDocumentView:
    """One validated flow document returned to the local Dashboard editor."""

    flow_id: str
    name: str
    enabled: bool
    brief: str
    path: str
    valid: bool
    content: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilitySummaryView:
    """Display-safe metadata for one Workspace capability."""

    capability_id: str
    name: str
    enabled: bool
    brief: str
    path: str
    valid: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilityDocumentView:
    """One validated capability document returned to the local Dashboard editor."""

    capability_id: str
    name: str
    enabled: bool
    brief: str
    path: str
    valid: bool
    content: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AgentObservabilitySettingsView:
    """Display-safe Langfuse settings for the local Agent."""

    enabled: bool
    provider: str
    base_url: str
    sample_rate: float
    public_key_configured: bool
    secret_key_configured: bool
    public_key_masked: str | None
    secret_key_masked: str | None


@dataclass(frozen=True, slots=True)
class AgentSettingsView:
    """Display-safe global Agent settings."""

    enabled: bool
    default_workspace_id: UUID | None
    agent_provider: str
    agent_model: str
    agent_reasoning_effort: str
    feishu_app_id: str
    feishu_app_configured: bool
    feishu_app_secret_masked: str | None
    observability: AgentObservabilitySettingsView


@dataclass(frozen=True, slots=True)
class AgentObservabilitySettingsUpdate:
    """Requested Langfuse settings with optional secret replacements."""

    enabled: bool
    base_url: str
    sample_rate: float
    public_key: str | None = None
    secret_key: str | None = None
    clear_credentials: bool = False


@dataclass(frozen=True, slots=True)
class AgentSettingsUpdate:
    """Requested global Agent settings."""

    enabled: bool
    default_workspace_id: UUID | None
    agent_model: str
    agent_reasoning_effort: AgentReasoningEffort
    feishu_app_id: str
    feishu_app_secret: str | None
    observability: AgentObservabilitySettingsUpdate


class DashboardService:
    """Coordinate Dashboard use cases behind a small typed interface."""

    def __init__(
        self,
        state_root: Path | None = None,
        registry: WorkspaceRegistry | None = None,
        settings_store: WorkspaceSettingsStore | None = None,
        initializer: WorkspaceInitializer | None = None,
        webhook_sender: FeishuWebhookSender | None = None,
        repository_provisioner: RepositoryProvisioner | None = None,
        folder_picker: Callable[[], Path | None] | None = None,
        agent_config_store: AgentConfigStore | None = None,
        delivery_scheduler: DeliveryScheduler | None = None,
        scan_scheduler: ScanScheduler | None = None,
        scan_service: ScanService | None = None,
    ) -> None:
        self.registry = registry or WorkspaceRegistry(state_root)
        self.settings_store = settings_store or WorkspaceSettingsStore(state_root)
        agent_state_root = state_root or self.registry.layout.root
        self.agent_config_store = agent_config_store or AgentConfigStore(agent_state_root)
        self.initializer = initializer or WorkspaceInitializer(
            registry=self.registry,
            settings_store=self.settings_store,
        )
        self.webhook_sender = webhook_sender or FeishuWebhookSender()
        self.repository_provisioner = repository_provisioner or RepositoryProvisioner()
        self._folder_picker = folder_picker or FolderPicker().choose
        self.delivery_scheduler = delivery_scheduler or LaunchdDeliveryScheduler(
            self.registry.layout.root
        )
        self.scan_scheduler = scan_scheduler or LaunchdScanScheduler(self.registry.layout.root)
        self.scan_service = scan_service or ScanService(
            state_root=self.registry.layout.root,
            registry=self.registry,
            settings_store=self.settings_store,
            agent_config_store=self.agent_config_store,
        )

    def list_workspaces(self) -> tuple[WorkspaceListItem, ...]:
        """Return registered Workspaces without scanning unregistered directories."""

        return tuple(self._health(item) for item in self.registry.list())

    def select_workspace_folder(self) -> Path | None:
        """Open the local folder selector for the Dashboard onboarding flow."""

        return self._folder_picker()

    def register_workspace(self, path: Path) -> WorkspaceRegistration:
        """Validate and register an existing Workspace, creating its profile."""

        canonical = path.expanduser().resolve()
        layout = WorkspaceLayout.from_root(canonical)
        manifest = load_manifest(layout.manifest)
        registry_snapshot = self.registry.raw_snapshot()
        profile_snapshot = self.settings_store.raw_snapshot(manifest.workspace_id)
        try:
            registration = self.registry.register(canonical)
            self.settings_store.ensure(manifest.workspace_id)
            return registration
        except Exception:
            self.settings_store.restore_raw(manifest.workspace_id, profile_snapshot)
            self.registry.restore_raw(registry_snapshot)
            raise

    def initialize_workspace(
        self,
        path: Path,
        name: str | None,
        repository_urls: tuple[str, ...],
    ) -> tuple[InitResult, WorkspaceRegistration]:
        """Initialize through the CLI domain flow and return the new registry entry."""

        specifications = tuple(spec_from_url(url) for url in repository_urls)
        result = self.initializer.initialize(
            InitRequest(path, name=name, repositories=specifications)
        )
        registration = self.registry.find_by_path(result.workspace)
        if registration is None:
            raise PreflightError(
                f"Workspace was initialized but not registered: {result.workspace}"
            )
        self._set_default_for_sole_workspace()
        return result, registration

    def overview(self, workspace_id: UUID) -> WorkspaceOverview:
        """Read manifest and Repository health for one registered Workspace."""

        registration = self._require(workspace_id)
        layout = WorkspaceLayout.from_root(registration.path)
        manifest = load_manifest(layout.manifest)
        config = load_workspace_config(layout.workspace_config)
        repositories: list[RepositoryOverview] = []
        for record in config.repositories:
            ok, detail = self.repository_provisioner.inspect(layout.root, record)
            repositories.append(
                RepositoryOverview(
                    name=record.name,
                    path=layout.root / record.path,
                    branch=record.branch,
                    health="ready" if ok else "unhealthy",
                    detail=detail,
                )
            )
        return WorkspaceOverview(
            workspace_id=manifest.workspace_id,
            name=manifest.name,
            path=layout.root,
            created_at=manifest.created_at,
            lumon_version=manifest.lumon_version,
            repositories=tuple(repositories),
        )

    def settings(self, workspace_id: UUID) -> WorkspaceSettingsView:
        """Read display-safe settings for one registered Workspace."""

        self._require(workspace_id)
        settings = self.settings_store.load(workspace_id)
        return _settings_view(settings)

    def scans(self, workspace_id: UUID) -> tuple[ScanRun, ...]:
        """Return recent Auto Scan receipts for one Workspace."""

        registration = self._require(workspace_id)
        return self.scan_service.list_runs(registration.path)

    def start_scan(self, workspace_id: UUID) -> ScanRun:
        """Start a manual Auto Scan even when its schedule is disabled."""

        self._require(workspace_id)
        return self.scan_service.run(workspace_id, force=True)

    def scan_artifact(self, workspace_id: UUID, run_id: str, kind: str) -> Path:
        """Return a safe report artifact path for the local Dashboard."""

        registration = self._require(workspace_id)
        return self.scan_service.artifact_path(registration.path, run_id, kind)

    def flows(self, workspace_id: UUID) -> tuple[FlowSummaryView, ...]:
        """List valid and invalid flow files for one Workspace."""

        registration = self._require(workspace_id)
        catalog = FlowCatalog(registration.path)
        snapshot = catalog.discover()
        summaries = [_flow_summary(item) for item in snapshot.definitions]
        summaries.extend(
            FlowSummaryView(
                flow_id=item.path.stem,
                name=item.path.name,
                enabled=False,
                brief="",
                path=_relative_flow_path(registration.path, item.path),
                valid=False,
                error=item.message,
            )
            for item in snapshot.diagnostics
        )
        return tuple(summaries)

    def flow(self, workspace_id: UUID, flow_id: str) -> FlowDocumentView:
        """Read one flow for the Dashboard editor, including invalid source."""

        registration = self._require(workspace_id)
        catalog = FlowCatalog(registration.path)
        try:
            return _flow_document(catalog.read(flow_id))
        except FlowValidationError as validation_error:
            try:
                path, content = catalog.read_raw(flow_id)
            except FlowValidationError:
                raise validation_error from None
            return FlowDocumentView(
                flow_id=flow_id,
                name=path.stem,
                enabled=False,
                brief="",
                path=path.as_posix(),
                valid=False,
                content=content,
                error=str(validation_error),
            )

    def create_flow(self, workspace_id: UUID, content: str) -> FlowDocumentView:
        """Create a flow file from Dashboard-provided Markdown."""

        registration = self._require(workspace_id)
        definition = FlowCatalog(registration.path).create(content)
        return _flow_document(definition)

    def update_flow(self, workspace_id: UUID, flow_id: str, content: str) -> FlowDocumentView:
        """Replace one flow while keeping its stable ID and file path."""

        registration = self._require(workspace_id)
        definition = FlowCatalog(registration.path).save(content, expected_id=flow_id)
        return _flow_document(definition)

    def delete_flow(self, workspace_id: UUID, flow_id: str) -> None:
        """Delete one user-authored flow file."""

        registration = self._require(workspace_id)
        FlowCatalog(registration.path).delete(flow_id)

    def capabilities(self, workspace_id: UUID) -> tuple[CapabilitySummaryView, ...]:
        """List valid and invalid capability files for one Workspace."""

        registration = self._require(workspace_id)
        catalog = CapabilityCatalog(registration.path)
        snapshot = catalog.discover()
        summaries = [_capability_summary(item) for item in snapshot.definitions]
        summaries.extend(
            CapabilitySummaryView(
                capability_id=item.path.stem,
                name=item.path.name,
                enabled=False,
                brief="",
                path=_relative_capability_path(registration.path, item.path),
                valid=False,
                error=item.message,
            )
            for item in snapshot.diagnostics
        )
        return tuple(summaries)

    def capability(
        self,
        workspace_id: UUID,
        capability_id: str,
    ) -> CapabilityDocumentView:
        """Read one capability for the Dashboard editor, including invalid source."""

        registration = self._require(workspace_id)
        catalog = CapabilityCatalog(registration.path)
        try:
            return _capability_document(catalog.read(capability_id))
        except CapabilityValidationError as validation_error:
            try:
                path, content = catalog.read_raw(capability_id)
            except CapabilityValidationError:
                raise validation_error from None
            return CapabilityDocumentView(
                capability_id=capability_id,
                name=path.stem,
                enabled=False,
                brief="",
                path=path.as_posix(),
                valid=False,
                content=content,
                error=str(validation_error),
            )

    def create_capability(
        self,
        workspace_id: UUID,
        content: str,
    ) -> CapabilityDocumentView:
        """Create a capability file from Dashboard-provided Markdown."""

        registration = self._require(workspace_id)
        definition = CapabilityCatalog(registration.path).create(content)
        return _capability_document(definition)

    def update_capability(
        self,
        workspace_id: UUID,
        capability_id: str,
        content: str,
    ) -> CapabilityDocumentView:
        """Replace one capability while keeping its stable ID and file path."""

        registration = self._require(workspace_id)
        definition = CapabilityCatalog(registration.path).save(
            content,
            expected_id=capability_id,
        )
        return _capability_document(definition)

    def delete_capability(self, workspace_id: UUID, capability_id: str) -> None:
        """Delete one user-authored capability file."""

        registration = self._require(workspace_id)
        CapabilityCatalog(registration.path).delete(capability_id)

    def agent_settings(self) -> AgentSettingsView:
        """Read display-safe global Agent settings."""

        return _agent_settings_view(self._load_agent_config())

    def update_agent_settings(self, update: AgentSettingsUpdate) -> AgentSettingsView:
        """Validate and persist global Agent settings."""

        current = self._load_agent_config()
        default_workspace_id = self._resolve_default_workspace_id(update.default_workspace_id)

        current_observability = current.observability
        next_observability = AgentObservabilitySettingsUpdate(
            enabled=update.observability.enabled,
            base_url=update.observability.base_url.strip(),
            sample_rate=update.observability.sample_rate,
            public_key=update.observability.public_key,
            secret_key=update.observability.secret_key,
            clear_credentials=update.observability.clear_credentials,
        )
        config = AgentConfig(
            enabled=update.enabled,
            default_workspace_id=default_workspace_id,
            agent_provider=current.agent_provider,
            agent_model=update.agent_model.strip(),
            agent_reasoning_effort=update.agent_reasoning_effort,
            feishu_app_id=update.feishu_app_id.strip(),
            feishu_app_secret=_updated_secret(
                current.feishu_app_secret,
                update.feishu_app_secret,
            ),
            observability=ObservabilityConfig(
                enabled=next_observability.enabled,
                provider=current_observability.provider,
                base_url=next_observability.base_url,
                sample_rate=next_observability.sample_rate,
                public_key=_updated_secret(
                    current_observability.public_key,
                    next_observability.public_key,
                    next_observability.clear_credentials,
                ),
                secret_key=_updated_secret(
                    current_observability.secret_key,
                    next_observability.secret_key,
                    next_observability.clear_credentials,
                ),
            ),
        )
        self.agent_config_store.save(config)
        return _agent_settings_view(config)

    def update_settings(
        self,
        workspace_id: UUID,
        enabled: bool,
        url_provided: bool,
        url: str | None,
        auto_delivery_enabled: bool | None = None,
        auto_delivery_trigger_hooks: tuple[str, ...] | None = None,
        auto_delivery_schedule_expression: str | None = None,
        auto_scan_enabled: bool | None = None,
        auto_scan_lookback_days: int | None = None,
        auto_scan_trigger_hooks: tuple[str, ...] | None = None,
        auto_scan_schedule_expression: str | None = None,
        auto_scan_workflow_description: str | None = None,
    ) -> WorkspaceSettingsView:
        """Update typed settings while retaining or clearing URL explicitly."""

        registration = self._require(workspace_id)
        current = self.settings_store.load(workspace_id)
        next_url = current.feishu_webhook.url
        if url_provided:
            next_url = url.strip() if url and url.strip() else None
            if next_url:
                validate_webhook_url(next_url)
        updated = WorkspaceSettings(
            workspace_id=workspace_id,
            feishu_webhook=FeishuWebhookSettings(enabled=enabled, url=next_url),
            auto_delivery=AutoDeliverySettings(
                enabled=(
                    current.auto_delivery.enabled
                    if auto_delivery_enabled is None
                    else auto_delivery_enabled
                ),
                trigger_hooks=(
                    current.auto_delivery.trigger_hooks
                    if auto_delivery_trigger_hooks is None
                    else auto_delivery_trigger_hooks
                ),
                schedule_expression=(
                    current.auto_delivery.schedule_expression
                    if auto_delivery_schedule_expression is None
                    else auto_delivery_schedule_expression
                ),
            ),
            auto_scan=AutoScanSettings(
                enabled=(
                    current.auto_scan.enabled if auto_scan_enabled is None else auto_scan_enabled
                ),
                lookback_days=(
                    current.auto_scan.lookback_days
                    if auto_scan_lookback_days is None
                    else auto_scan_lookback_days
                ),
                trigger_hooks=(
                    current.auto_scan.trigger_hooks
                    if auto_scan_trigger_hooks is None
                    else auto_scan_trigger_hooks
                ),
                schedule_expression=(
                    current.auto_scan.schedule_expression
                    if auto_scan_schedule_expression is None
                    else auto_scan_schedule_expression
                ),
                workflow_description=(
                    current.auto_scan.workflow_description
                    if auto_scan_workflow_description is None
                    else auto_scan_workflow_description
                ),
            ),
        )
        snapshot = self.settings_store.raw_snapshot(workspace_id)
        try:
            self.settings_store.save(updated)
            self.delivery_scheduler.apply(
                registration.path,
                workspace_id,
                updated.auto_delivery,
            )
            self.scan_scheduler.apply(registration.path, workspace_id, updated.auto_scan)
        except LumonError:
            self.settings_store.restore_raw(workspace_id, snapshot)
            raise
        return _settings_view(updated)

    def test_feishu_webhook(
        self,
        workspace_id: UUID,
        url_provided: bool,
        url: str | None,
    ) -> WebhookTestResult:
        """Test a saved or draft URL without persisting or returning it."""

        self._require(workspace_id)
        saved = self.settings_store.load(workspace_id).feishu_webhook.url
        candidate = (url.strip() if url and url.strip() else None) if url_provided else saved
        if not candidate:
            raise PreflightError("Feishu Webhook URL is not configured.")
        return self.webhook_sender.send_test(candidate)

    def _require(self, workspace_id: UUID) -> WorkspaceRegistration:
        registration = self.registry.find(workspace_id)
        if registration is None:
            raise WorkspaceNotFoundError(f"Workspace is not registered: {workspace_id}")
        return registration

    def _load_agent_config(self) -> AgentConfig:
        try:
            return self.agent_config_store.load()
        except AgentConfigError:
            if not self.agent_config_store.path.exists():
                return AgentConfig()
            raise

    def _resolve_default_workspace_id(self, requested: UUID | None) -> UUID | None:
        if requested is not None:
            self._require(requested)
            return requested
        registrations = self.registry.list()
        if len(registrations) == 1:
            return registrations[0].workspace_id
        return None

    def _set_default_for_sole_workspace(self) -> None:
        registrations = self.registry.list()
        if len(registrations) != 1:
            return
        try:
            config = self.agent_config_store.load()
        except AgentConfigError:
            return
        workspace_id = registrations[0].workspace_id
        if config.default_workspace_id == workspace_id:
            return
        self.agent_config_store.save(replace(config, default_workspace_id=workspace_id))

    def _health(self, registration: WorkspaceRegistration) -> WorkspaceListItem:
        if not registration.path.is_dir():
            return WorkspaceListItem(registration, "missing", "Workspace directory is missing.")
        layout = WorkspaceLayout.from_root(registration.path)
        try:
            manifest = load_manifest(layout.manifest)
            if manifest.workspace_id != registration.workspace_id:
                raise PreflightError("Workspace manifest ID differs from the registry.")
        except Exception as exc:
            return WorkspaceListItem(registration, "invalid", str(exc))
        return WorkspaceListItem(registration, "ready", "Workspace is available.")


def _settings_view(settings: WorkspaceSettings) -> WorkspaceSettingsView:
    webhook = settings.feishu_webhook
    return WorkspaceSettingsView(
        workspace_id=settings.workspace_id,
        feishu_webhook=WebhookSettingsView(
            enabled=webhook.enabled,
            configured=bool(webhook.url),
            masked_url=masked_webhook_url(webhook.url),
        ),
        auto_delivery=AutoDeliverySettingsView(
            enabled=settings.auto_delivery.enabled,
            trigger_hooks=settings.auto_delivery.trigger_hooks,
            schedule_expression=settings.auto_delivery.schedule_expression,
        ),
        auto_scan=AutoScanSettingsView(
            enabled=settings.auto_scan.enabled,
            lookback_days=settings.auto_scan.lookback_days,
            trigger_hooks=settings.auto_scan.trigger_hooks,
            schedule_expression=settings.auto_scan.schedule_expression,
            workflow_description=settings.auto_scan.workflow_description,
        ),
    )


def _flow_summary(definition: FlowDefinition) -> FlowSummaryView:
    return FlowSummaryView(
        flow_id=definition.flow_id,
        name=definition.name,
        enabled=definition.enabled,
        brief=definition.brief,
        path=definition.path.as_posix(),
        valid=True,
    )


def _flow_document(definition: FlowDefinition) -> FlowDocumentView:
    summary = _flow_summary(definition)
    return FlowDocumentView(
        flow_id=summary.flow_id,
        name=summary.name,
        enabled=summary.enabled,
        brief=summary.brief,
        path=summary.path,
        valid=True,
        content=definition.content,
    )


def _capability_summary(definition: CapabilityDefinition) -> CapabilitySummaryView:
    return CapabilitySummaryView(
        capability_id=definition.capability_id,
        name=definition.name,
        enabled=definition.enabled,
        brief=definition.brief,
        path=definition.path.as_posix(),
        valid=True,
    )


def _capability_document(definition: CapabilityDefinition) -> CapabilityDocumentView:
    summary = _capability_summary(definition)
    return CapabilityDocumentView(
        capability_id=summary.capability_id,
        name=summary.name,
        enabled=summary.enabled,
        brief=summary.brief,
        path=summary.path,
        valid=True,
        content=definition.content,
    )


def _relative_flow_path(workspace: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.expanduser().resolve()).as_posix()
    except ValueError:
        return path.name


def _relative_capability_path(workspace: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.expanduser().resolve()).as_posix()
    except ValueError:
        return path.name


def _agent_settings_view(config: AgentConfig) -> AgentSettingsView:
    observability = config.observability
    feishu_app_secret = _configured_credential(config.feishu_app_secret)
    public_key = _configured_credential(observability.public_key, "LANGFUSE_PUBLIC_KEY")
    secret_key = _configured_credential(observability.secret_key, "LANGFUSE_SECRET_KEY")
    return AgentSettingsView(
        enabled=config.enabled,
        default_workspace_id=config.default_workspace_id,
        agent_provider=config.agent_provider,
        agent_model=config.agent_model,
        agent_reasoning_effort=config.agent_reasoning_effort,
        feishu_app_id=config.feishu_app_id,
        feishu_app_configured=feishu_app_secret is not None,
        feishu_app_secret_masked=masked_secret(feishu_app_secret),
        observability=AgentObservabilitySettingsView(
            enabled=observability.enabled,
            provider=observability.provider,
            base_url=observability.base_url,
            sample_rate=observability.sample_rate,
            public_key_configured=public_key is not None,
            secret_key_configured=secret_key is not None,
            public_key_masked=masked_secret(public_key),
            secret_key_masked=masked_secret(secret_key),
        ),
    )


def _configured_credential(value: str, environment_name: str | None = None) -> str | None:
    if value.strip():
        return value
    if environment_name is None:
        return None
    environment_value = os.environ.get(environment_name, "")
    return environment_value if environment_value.strip() else None


def _updated_secret(current: str, replacement: str | None, clear: bool = False) -> str:
    if clear:
        return ""
    if replacement is None or not replacement.strip():
        return current
    return replacement.strip()
