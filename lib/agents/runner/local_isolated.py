from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable, Protocol

from agents.definitions import AgentDefinition
from agents.runtime.cursor_runtime import AgentRunResult, CursorAgentRuntime
from agents.runtime.observability import Observability, TraceContext
from agents.runtime.connected_tools import ConnectedToolExecutor
from agents.runtime.native_tool_server import NativeToolDispatcher
from agents.runtime.native_context import ensure_workspace_context
from agents.runner.isolation import DisposableWorkspace, IsolationError
from agents.runner.agent_world import AgentWorld, AgentWorldError
from agents.runner.runner_env import build_runner_env, build_trusted_runner_env
from agents.security.flags import (
    isolated_agent_world_enabled,
    trusted_dedicated_machine_enabled,
    workspace_isolation_v2_enabled,
)
from agents.security.tools import write_host_tool_manifest
from agents.security.trusted import trusted_context_from_meta
from feishu.config import agents_home


class AgentRunner(Protocol):
    def run(
        self,
        *,
        definition: AgentDefinition,
        workspace: Path,
        prompt: str,
        provider_session_id: str | None,
        trace: TraceContext,
        obs: Observability | None = None,
        on_event: Callable[[Any], Any] | None = None,
    ) -> AgentRunResult: ...


class LocalIsolatedAgentRunner:
    requires_definition = True

    def __init__(
        self,
        *,
        runtime: CursorAgentRuntime | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.runtime = runtime
        self.config = config if isinstance(config, dict) else None

    def run(
        self,
        *,
        definition: AgentDefinition,
        workspace: Path,
        prompt: str,
        provider_session_id: str | None,
        trace: TraceContext,
        obs: Observability | None = None,
        on_event: Callable[[Any], Any] | None = None,
    ) -> AgentRunResult:
        agent_id = str(definition.id or "").strip().lower()
        project = str(getattr(trace, "project_slug", "") or "")
        runtime = self.runtime or CursorAgentRuntime(
            sandbox="unrestricted",
            force=False,
            trust=True,
            agent_id=agent_id,
            project=project,
        )
        # The named M0.8 mode is authoritative. Keep the old boolean as a
        # fail-closed compatibility signal for pre-M0.8 callers that did not
        # persist a mode yet.
        if trusted_dedicated_machine_enabled(self.config) or not (
            isolated_agent_world_enabled(self.config) or workspace_isolation_v2_enabled(self.config)
        ):
            return runtime.run(
                workspace=workspace,
                prompt=prompt,
                provider_session_id=provider_session_id,
                trace=trace,
                obs=obs,
                on_event=on_event,
            )

        layer: DisposableWorkspace | None = None
        world: AgentWorld | None = None
        native_dispatcher: NativeToolDispatcher | None = None
        try:
            layer = DisposableWorkspace.create(workspace, agent_id)
            world = AgentWorld.create(
                canonical=workspace,
                workspace=layer.path,
                agent_id=agent_id,
                require_boundary=True,
            )
        except (IsolationError, AgentWorldError, OSError) as exc:
            try:
                if layer is not None:
                    layer.close()
            except Exception:
                pass
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                status="security_error",
                error=f"ISOLATION_INITIALIZATION_FAILED: {str(exc)[:400]}",
            )

        _missing = object()
        original_env = getattr(runtime, "isolated_env", _missing)
        original_dirs = list(getattr(runtime, "additional_dirs", [])) if hasattr(runtime, "additional_dirs") else None
        original_files = list(getattr(runtime, "additional_files", [])) if hasattr(runtime, "additional_files") else None
        original_directories = list(getattr(runtime, "additional_directories", [])) if hasattr(runtime, "additional_directories") else None
        original_prefix = list(getattr(runtime, "command_prefix", []))
        try:
            write_host_tool_manifest(layer.path)
            from agents.runtime.native_tool_bridge import write_native_tool_manifests

            write_native_tool_manifests(layer.path, provider=runtime.__class__.__name__)
            runtime.isolated_env = build_runner_env(
                agent_id=agent_id,
                project=project,
                config=self.config,
                world=world,
                gate=getattr(runtime, "entry_gate", None),
            )
            runtime.isolated_env["LUMON_NATIVE_TOOL_MANIFEST"] = str(layer.path / ".lumon" / "native-tools.json")
            runtime.isolated_env["LUMON_NATIVE_TOOL_CONFIG"] = str(layer.path / ".lumon" / "mcp.json")
            entry_gate = getattr(runtime, "entry_gate", None)
            if entry_gate is not None:
                gate_decision = getattr(entry_gate, "decision", None)
                gate_context = getattr(gate_decision, "context", None)
                gate_meta = {
                    "user_id": str(getattr(entry_gate, "user_id", "") or ""),
                    "chat_id": str(getattr(entry_gate, "chat_id", "") or ""),
                    "thread_id": str(getattr(entry_gate, "thread_id", "") or ""),
                    "message_id": str(getattr(entry_gate, "message_id", "") or ""),
                    "chat_type": str(getattr(gate_context, "chat_type", "") or ""),
                    "chat_name": str(getattr(gate_context, "chat_name", "") or ""),
                    "root_id": str(getattr(gate_context, "root_id", "") or ""),
                    "participants": list(getattr(gate_context, "participants", ()) or ()),
                    "available_agents": list(getattr(gate_context, "available_agents", ()) or ()),
                    "available_agents_verified": bool(getattr(gate_context, "available_agents_verified", False)),
                    "_entry_gate_token": str(getattr(entry_gate, "token", "") or ""),
                }
                host_context = trusted_context_from_meta(
                    agent_id=agent_id,
                    project_slug=project,
                    meta=gate_meta,
                    trace_id=str(getattr(trace, "trace_id", "") or ""),
                    access_decision=gate_decision,
                )
                native_dispatcher = NativeToolDispatcher(
                    # AF_UNIX paths are short (roughly 104 bytes on macOS),
                    # so keep the bridge socket in the stable Agent World
                    # root rather than under a long disposable temp path.
                    socket_path=world.spec.root / f"{world.spec.world_id}.sock",
                    executor=ConnectedToolExecutor(),
                    context=host_context,
                ).start()
                runtime.isolated_env["LUMON_NATIVE_TOOL_SOCKET"] = str(native_dispatcher.socket_path)
            # The provider subprocess, not the Python Host, crosses the OS
            # boundary. Provider adapters prepend this immutable command
            # prefix to their executable invocation.
            runtime.command_prefix = list(world.spec.command_prefix)
            external: list[Path] = []
            external_keys: set[str] = set()

            def add_external(values: list[Path] | None) -> None:
                for item in values or []:
                    path = Path(item).expanduser().resolve()
                    key = str(path)
                    if key not in external_keys:
                        external_keys.add(key)
                        external.append(path)

            add_external(original_dirs)
            add_external(original_files)
            add_external(original_directories)
            staged = layer.stage_paths(external)
            if hasattr(runtime, "additional_dirs"):
                runtime.additional_dirs = [path for path in staged if path.is_dir()]
            if hasattr(runtime, "additional_files"):
                runtime.additional_files = [path for path in staged if path.is_file()]
            if hasattr(runtime, "additional_directories"):
                runtime.additional_directories = [path for path in staged if path.is_dir()]

            run_prompt = str(prompt or "").replace(str(Path(workspace).expanduser().resolve()), str(layer.path))
            result = runtime.run(
                workspace=layer.path,
                prompt=run_prompt,
                provider_session_id=provider_session_id,
                trace=trace,
                obs=obs,
                on_event=on_event,
            )
            if result.status == "succeeded":
                receipt = layer.publish()
                if receipt.status != "succeeded":
                    result.status = "security_error"
                    result.error = f"{receipt.code}: {', '.join(receipt.deleted_files)}"
                if obs and trace:
                    obs.emit(
                        trace,
                        "workspace.publish.blocked" if receipt.status != "succeeded" else "workspace.publish.completed",
                        **receipt.to_dict(),
                        level="ERROR" if receipt.status != "succeeded" else "INFO",
                    )
            return result
        except (IsolationError, OSError) as exc:
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                status="security_error",
                error=f"ISOLATION_PUBLISH_FAILED: {str(exc)[:400]}",
            )
        finally:
            if original_env is not _missing:
                runtime.isolated_env = original_env
            if original_dirs is not None:
                runtime.additional_dirs = original_dirs
            if original_files is not None:
                runtime.additional_files = original_files
            if original_directories is not None:
                runtime.additional_directories = original_directories
            runtime.command_prefix = original_prefix
            if world is not None:
                world.close()
            if native_dispatcher is not None:
                native_dispatcher.close()
            if layer is not None:
                layer.close()


class TrustedAgentRunner:
    """Run a provider directly in the dedicated host-user Agent World.

    There is deliberately no disposable layer, sandbox-exec prefix or
    publication step here.  The only Host-owned seam is the Feishu entry gate
    and the native connected-tool dispatcher, which gives providers their
    normal CLI/OS capability while preserving identity and audit receipts.
    """

    requires_definition = True

    def __init__(self, *, runtime: CursorAgentRuntime | None = None, config: dict[str, Any] | None = None) -> None:
        self.runtime = runtime
        self.config = config if isinstance(config, dict) else {}

    def run(
        self,
        *,
        definition: AgentDefinition,
        workspace: Path,
        prompt: str,
        provider_session_id: str | None,
        trace: TraceContext,
        obs: Observability | None = None,
        on_event: Callable[[Any], Any] | None = None,
    ) -> AgentRunResult:
        agent_id = str(definition.id or "").strip().lower()
        project = str(getattr(trace, "project_slug", "") or "")
        workspace = Path(workspace).expanduser().resolve()
        runtime = self.runtime or CursorAgentRuntime(
            sandbox="unrestricted",
            force=False,
            trust=True,
            agent_id=agent_id,
            project=project,
            harness_mode="trusted_dedicated_machine",
        )
        ensure_workspace_context(workspace, agent_id=agent_id)
        write_host_tool_manifest(workspace)
        from agents.runtime.native_tool_bridge import write_native_tool_manifests

        write_native_tool_manifests(workspace, provider=runtime.__class__.__name__)

        entry_gate = getattr(runtime, "entry_gate", None)
        gate_decision = getattr(entry_gate, "decision", None)
        gate_context = getattr(gate_decision, "context", None)
        gate_meta = {
            "user_id": str(getattr(entry_gate, "user_id", "") or ""),
            "chat_id": str(getattr(entry_gate, "chat_id", "") or ""),
            "thread_id": str(getattr(entry_gate, "thread_id", "") or ""),
            "message_id": str(getattr(entry_gate, "message_id", "") or ""),
            "chat_type": str(getattr(gate_context, "chat_type", "") or ""),
            "chat_name": str(getattr(gate_context, "chat_name", "") or ""),
            "root_id": str(getattr(gate_context, "root_id", "") or ""),
            "participants": list(getattr(gate_context, "participants", ()) or ()),
            "available_agents": list(getattr(gate_context, "available_agents", ()) or ()),
            "available_agents_verified": bool(getattr(gate_context, "available_agents_verified", False)),
            "_entry_gate_token": str(getattr(entry_gate, "token", "") or ""),
        }
        host_context = trusted_context_from_meta(
            agent_id=agent_id,
            project_slug=project,
            meta=gate_meta,
            trace_id=str(getattr(trace, "trace_id", "") or ""),
            access_decision=gate_decision,
        )
        native_dispatcher: NativeToolDispatcher | None = None
        _missing = object()
        original_env = getattr(runtime, "isolated_env", _missing)
        original_gate = getattr(runtime, "entry_gate", _missing)
        socket_path = agents_home() / "native-tools" / f"{agent_id or 'agent'}-{uuid.uuid4().hex}.sock"
        try:
            native_dispatcher = NativeToolDispatcher(
                socket_path=socket_path,
                executor=ConnectedToolExecutor(),
                context=host_context,
            ).start()
            runtime.entry_gate = entry_gate
            runtime.isolated_env = build_trusted_runner_env(
                agent_id=agent_id,
                project=project,
                config=self.config,
                gate=entry_gate,
                workspace=workspace,
                native_socket=str(native_dispatcher.socket_path),
            )
            runtime.isolated_env["LUMON_GATE_TRACE_ID"] = str(getattr(trace, "trace_id", "") or "")
            runtime.isolated_env["LUMON_NATIVE_TOOL_MANIFEST"] = str(workspace / ".lumon" / "native-tools.json")
            runtime.isolated_env["LUMON_NATIVE_TOOL_CONFIG"] = str(workspace / ".lumon" / "mcp.json")
            if obs and trace:
                obs.emit(
                    trace,
                    "agent.trusted_world.started",
                    runner="trusted_dedicated_machine",
                    workspace=str(workspace),
                    identity="host_user",
                    provider=runtime.__class__.__name__,
                )
            return runtime.run(
                workspace=workspace,
                prompt=prompt,
                provider_session_id=provider_session_id,
                trace=trace,
                obs=obs,
                on_event=on_event,
            )
        finally:
            if obs and trace:
                obs.emit(trace, "agent.trusted_world.finished", runner="trusted_dedicated_machine")
            if original_env is not _missing:
                runtime.isolated_env = original_env
            if original_gate is not _missing:
                runtime.entry_gate = original_gate
            if native_dispatcher is not None:
                native_dispatcher.close()


def default_runner(
    *,
    runtime: CursorAgentRuntime | None = None,
    config: dict[str, Any] | None = None,
) -> LocalIsolatedAgentRunner | TrustedAgentRunner:
    if trusted_dedicated_machine_enabled(config):
        return TrustedAgentRunner(runtime=runtime, config=config)
    return LocalIsolatedAgentRunner(runtime=runtime, config=config)
