"""Execute an exact saved Workflow independently of its scheduling policy."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from lumon.agents.agent.config import AgentConfigStore
from lumon.agents.agent.model import AgentResult
from lumon.agents.agent.runner import AgentRunner, create_agent_runner
from lumon.agents.agent.workspace_context import WorkspaceContextBuilder
from lumon.errors import AgentRuntimeError, PreflightError
from lumon.flows.catalog import FlowCatalog
from lumon.flows.scheduler import flow_lock
from lumon.tools.safety import sanitize_output
from lumon.workspace.registry import WorkspaceRegistry


class FlowService:
    """Share prompt construction and overlap protection between manual and scheduled runs."""

    def __init__(
        self,
        registry: WorkspaceRegistry | None = None,
        agent_config_store: AgentConfigStore | None = None,
        runner: AgentRunner | None = None,
    ) -> None:
        self.registry = registry or WorkspaceRegistry()
        self.agent_config_store = agent_config_store or AgentConfigStore(self.registry.layout.root)
        self.runner = runner

    async def run(self, workspace_id: UUID, flow_id: str) -> AgentResult:
        """Run saved instructions without changing or requiring an enabled schedule."""

        registration = self.registry.find(workspace_id)
        if registration is None:
            raise PreflightError("The Workspace is not registered.")
        flow = FlowCatalog(registration.path).read(flow_id)
        if not flow.enabled:
            raise PreflightError("Enable this Workflow before running it.")
        config = self.agent_config_store.load()
        if not config.enabled:
            raise PreflightError("The Lumon Agent is disabled.")
        builder = WorkspaceContextBuilder(
            replace(config, default_workspace_id=workspace_id), self.registry
        )
        context = builder.resolve_workspace()
        prompt = builder.build_prompt(
            context, (), f"Run the Workspace Flow '{flow.flow_id}' now.", scheduled_flow=flow
        )
        runner = self.runner or create_agent_runner(config)
        with flow_lock(self.registry.layout.root, workspace_id, flow_id):
            result = await runner.run(context.path, prompt)
        if result.status != "succeeded":
            diagnostic = sanitize_output(result.failure_diagnostic or "Workflow did not complete.")
            raise AgentRuntimeError(diagnostic)
        return result
