"""Resolve a Workspace and build the bounded prompt sent to an Agent runner."""

from __future__ import annotations

from pathlib import Path

from lumon.agents.agent.config import AgentConfig
from lumon.agents.agent.model import Message, WorkspaceContext
from lumon.agents.agent.prompt import PromptRenderer
from lumon.agents.agent.soul import SoulLoader
from lumon.capabilities.catalog import CapabilityCatalog
from lumon.errors import AgentRuntimeError, WorkspaceNotFoundError
from lumon.flows.catalog import FlowCatalog
from lumon.workspace.config import load_workspace_config
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.registry import WorkspaceRegistration, WorkspaceRegistry


class WorkspaceContextBuilder:
    """Keep Workspace selection and prompt assembly behind one narrow interface."""

    def __init__(
        self,
        config: AgentConfig,
        registry: WorkspaceRegistry | None = None,
        soul_loader: SoulLoader | None = None,
        prompt_renderer: PromptRenderer | None = None,
    ) -> None:
        self.config = config
        self.registry = registry or WorkspaceRegistry()
        self.soul_loader = soul_loader or SoulLoader()
        self.prompt_renderer = prompt_renderer or PromptRenderer()

    def resolve_workspace(self) -> WorkspaceContext:
        """Resolve the configured or unique Workspace and validate its identity."""

        registration = self._select_registration()
        layout = WorkspaceLayout.from_root(registration.path)
        if not layout.root.is_dir():
            raise AgentRuntimeError(f"Configured Workspace path is unavailable: {layout.root}")

        try:
            manifest = load_manifest(layout.manifest)
            workspace_config = load_workspace_config(layout.workspace_config)
        except Exception as exc:
            if isinstance(exc, (AgentRuntimeError, WorkspaceNotFoundError)):
                raise
            raise AgentRuntimeError(
                f"Configured Workspace metadata is invalid: {layout.root}"
            ) from exc
        if manifest.workspace_id != registration.workspace_id:
            raise AgentRuntimeError(
                f"Workspace manifest ID does not match the registry: {layout.root}"
            )
        if workspace_config.name != manifest.name:
            raise AgentRuntimeError(
                f"Workspace name differs between manifest and configuration: {layout.root}"
            )

        agents_text = _read_agents(layout.agents_instructions)
        flow_snapshot = FlowCatalog(layout.root).discover()
        capability_snapshot = CapabilityCatalog(layout.root).discover()
        repositories = tuple(
            f"{record.name} ({record.path}, branch {record.branch})"
            for record in workspace_config.repositories
        )
        return WorkspaceContext(
            workspace_id=manifest.workspace_id,
            name=manifest.name,
            path=layout.root,
            agents_path=layout.agents_instructions,
            manifest_path=layout.manifest,
            workspace_config_path=layout.workspace_config,
            agents_text=agents_text,
            repositories=repositories,
            flow_briefs=flow_snapshot.briefs,
            capability_briefs=capability_snapshot.briefs,
        )

    def build_prompt(
        self,
        context: WorkspaceContext,
        history: tuple[Message, ...],
        user_message: str,
    ) -> str:
        """Build a self-contained Agent prompt from identity, rules, and history."""

        return self.prompt_renderer.render(
            context=context,
            history=history,
            soul=self.soul_loader.load(),
            user_message=user_message,
        )

    def build_resume_prompt(self, context: WorkspaceContext, user_message: str) -> str:
        """Build a small prompt that refreshes flow briefs for a resumed Session."""

        return self.prompt_renderer.render_resume(
            flow_briefs=FlowCatalog(context.path).discover().briefs,
            capability_briefs=CapabilityCatalog(context.path).discover().briefs,
            user_message=user_message,
        )

    def _select_registration(self) -> WorkspaceRegistration:
        if self.config.default_workspace_id is not None:
            registration = self.registry.find(self.config.default_workspace_id)
            if registration is None:
                raise WorkspaceNotFoundError(
                    f"Configured default Workspace is not registered: "
                    f"{self.config.default_workspace_id}"
                )
            return registration

        registrations: tuple[WorkspaceRegistration, ...] = self.registry.list()
        if not registrations:
            raise WorkspaceNotFoundError(
                "Agent has no Workspace. Initialize or register one before starting the Agent."
            )
        if len(registrations) > 1:
            raise AgentRuntimeError(
                "Agent has multiple Workspaces but no default_workspace_id is configured."
            )
        return next(iter(registrations))


def _read_agents(path: Path) -> str:
    if not path.exists():
        return "(AGENTS.md is not present.)"
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AgentRuntimeError(f"Unable to read Workspace instructions: {path}") from exc
