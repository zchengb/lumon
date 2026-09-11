"""Dashboard use cases over the typed Workspace and profile modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from lumon.dashboard.folder_picker import FolderPicker
from lumon.errors import PreflightError, WorkspaceNotFoundError
from lumon.tools.feishu_webhook import FeishuWebhookSender, WebhookTestResult, validate_webhook_url
from lumon.workspace.config import load_workspace_config
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.model import InitRequest, InitResult
from lumon.workspace.registry import WorkspaceRegistration, WorkspaceRegistry
from lumon.workspace.repositories import RepositoryProvisioner, spec_from_url
from lumon.workspace.settings import (
    FeishuWebhookSettings,
    WorkspaceSettings,
    WorkspaceSettingsStore,
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
    revision: str
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
class WorkspaceSettingsView:
    """The display-safe settings view for one Workspace."""

    workspace_id: UUID
    feishu_webhook: WebhookSettingsView


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
    ) -> None:
        self.registry = registry or WorkspaceRegistry(state_root)
        self.settings_store = settings_store or WorkspaceSettingsStore(state_root)
        self.initializer = initializer or WorkspaceInitializer(
            registry=self.registry,
            settings_store=self.settings_store,
        )
        self.webhook_sender = webhook_sender or FeishuWebhookSender()
        self.repository_provisioner = repository_provisioner or RepositoryProvisioner()
        self._folder_picker = folder_picker or FolderPicker().choose

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
                    revision=record.revision,
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

    def update_settings(
        self,
        workspace_id: UUID,
        enabled: bool,
        url_provided: bool,
        url: str | None,
    ) -> WorkspaceSettingsView:
        """Update typed settings while retaining or clearing URL explicitly."""

        self._require(workspace_id)
        current = self.settings_store.load(workspace_id)
        next_url = current.feishu_webhook.url
        if url_provided:
            next_url = url.strip() if url and url.strip() else None
            if next_url:
                validate_webhook_url(next_url)
        updated = WorkspaceSettings(
            workspace_id=workspace_id,
            feishu_webhook=FeishuWebhookSettings(enabled=enabled, url=next_url),
        )
        self.settings_store.save(updated)
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
    )
