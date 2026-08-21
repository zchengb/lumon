from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from agents.definitions import AgentDefinition
from agents.runtime.cursor_runtime import AgentRunResult, CursorAgentRuntime
from agents.runtime.observability import Observability, TraceContext
from agents.runtime.connected_tools import ConnectedToolExecutor
from agents.runtime.native_tool_server import NativeToolDispatcher
from agents.runner.isolation import DisposableWorkspace, IsolationError
from agents.runner.agent_world import AgentWorld, AgentWorldError
from agents.runner.runner_env import build_runner_env
from agents.security.flags import workspace_isolation_v2_enabled
from agents.security.tools import write_host_tool_manifest
from agents.security.trusted import trusted_context_from_meta


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
    def __init__(self, *, runtime: CursorAgentRuntime | None = None) -> None:
        self.runtime = runtime

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
        if not workspace_isolation_v2_enabled():
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


def default_runner(*, runtime: CursorAgentRuntime | None = None) -> LocalIsolatedAgentRunner:
    return LocalIsolatedAgentRunner(runtime=runtime)
