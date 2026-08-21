from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agents.definitions import AgentDefinition
from agents.runtime.cursor_runtime import AgentRunResult, CursorAgentRuntime
from agents.runtime.observability import Observability, TraceContext
from agents.runner.isolation import DisposableWorkspace, IsolationError
from agents.runner.runner_env import build_runner_env
from agents.security.flags import workspace_isolation_v2_enabled
from agents.security.tools import write_host_tool_manifest


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
            )

        try:
            layer = DisposableWorkspace.create(workspace, agent_id)
        except (IsolationError, OSError) as exc:
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
        try:
            write_host_tool_manifest(layer.path)
            runtime.isolated_env = build_runner_env(agent_id=agent_id, project=project)
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
            layer.close()


def default_runner(*, runtime: CursorAgentRuntime | None = None) -> LocalIsolatedAgentRunner:
    return LocalIsolatedAgentRunner(runtime=runtime)
