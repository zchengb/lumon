from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from agents.dylan.model_client import _load_lumen_dotenv
from agents.runtime.cursor_runtime import AgentRunResult
from agents.runtime.cursor_stream import AgentToolEvent
from agents.runtime.harness import HarnessCapabilities, capabilities_for_provider, canonical_task_mode, harness_mode as configured_harness_mode
from agents.runtime.harness_events import HarnessEvent, from_provider_event, normalize_provider_events
from agents.runtime.native_context import ensure_workspace_context


DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def find_opencode_bin() -> str:
    path = shutil.which("opencode")
    if path:
        return path
    candidates = [Path.home() / ".local" / "bin" / "opencode"]
    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    if nvm_root.is_dir():
        candidates.extend(sorted(nvm_root.glob("*/bin/opencode"), reverse=True))
    return next((str(path) for path in candidates if path.is_file() and os.access(path, os.X_OK)), "")


@dataclass
class OpenCodeStreamResult:
    text: str = ""
    provider_session_id: str = ""
    request_id: str = ""
    status: str = "failed"
    error: str = ""
    tool_events: list[AgentToolEvent] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


def parse_opencode_json_lines(lines: Iterable[str]) -> OpenCodeStreamResult:
    result = OpenCodeStreamResult()
    text_parts: list[str] = []
    for raw in lines:
        line = str(raw or "").strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(event, dict):
            continue
        result.events.append(event)
        session_id = str(event.get("sessionID") or event.get("session_id") or "").strip()
        if session_id:
            result.provider_session_id = session_id
        part = event.get("part") if isinstance(event.get("part"), dict) else {}
        request_id = event.get("requestID") or event.get("request_id") or part.get("messageID")
        if request_id:
            result.request_id = str(request_id)
        event_type = str(event.get("type") or "").strip().lower()
        if event_type == "text" or str(part.get("type") or "").strip().lower() == "text":
            value = part.get("text") or event.get("text") or ""
            if value:
                text_parts.append(str(value))
            continue
        if event_type in {"tool_use", "tool_call", "tool_result"} or part.get("tool"):
            tool = str(part.get("tool") or event.get("tool") or part.get("type") or event_type)
            call_id = str(part.get("callID") or part.get("call_id") or event.get("callID") or "")
            status = "completed" if event_type == "tool_result" else "started"
            result.tool_events.append(
                AgentToolEvent(
                    tool_type=tool[:80],
                    subtype=event_type,
                    call_id=call_id[:120],
                    status=status,
                    raw_summary=json.dumps({"tool": tool, "call_id": call_id}, ensure_ascii=False)[:240],
                )
            )
            continue
        if event_type == "error":
            error = event.get("error")
            result.error = str(error or "OpenCode returned an error")[:500]

    result.text = "".join(text_parts).strip()
    if result.text and not result.error:
        result.status = "succeeded"
    elif result.error:
        result.status = "failed"
    return result


def parse_opencode_json_text(text: str) -> OpenCodeStreamResult:
    return parse_opencode_json_lines(str(text or "").splitlines())


def _model_id(model: str) -> str:
    value = str(model or DEFAULT_MODEL).strip()
    return value.split("/", 1)[1] if "/" in value else value


def _model_provider(model: str, base_url: str = "") -> str:
    value = str(model or DEFAULT_MODEL).strip()
    if "/" in value:
        return value.split("/", 1)[0].strip() or "qwen"
    url = str(base_url or "").strip().casefold()
    if url.startswith(("http://127.0.0.1", "http://localhost", "http://0.0.0.0")):
        return "qwen"
    return "deepseek"


def is_local_opencode_provider(model: str, base_url: str = "") -> bool:
    return _model_provider(model, base_url) == "qwen"


class OpenCodeAgentRuntime:
    """Persistent OpenCode Harness using a configured OpenAI-compatible provider."""

    supports_stateless = False
    supports_resume = True
    uses_isolated_env = True

    def __init__(
        self,
        *,
        model: str = "",
        base_url: str = "",
        api_key_env: str = "",
        soft_timeout_seconds: int = 90,
        hard_timeout_seconds: int = 3600,
        sandbox: str = "unrestricted",
        force: bool = False,
        trust: bool = True,
        agent_id: str = "",
        project: str = "",
        harness_mode: str = "",
        task_mode: str = "",
        workflow_mode: bool = False,
        jira_read_actions: frozenset[str] | None = None,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        provider = _model_provider(self.model, base_url)
        self.base_url = base_url or (DEFAULT_BASE_URL if provider == "qwen" else DEEPSEEK_BASE_URL)
        self.api_key_env = api_key_env or ("" if provider == "qwen" else DEFAULT_API_KEY_ENV)
        self.soft_timeout_seconds = soft_timeout_seconds
        self.hard_timeout_seconds = hard_timeout_seconds
        self.sandbox = sandbox
        self.force = force
        self.trust = trust
        self.agent_id = agent_id
        self.project = project
        self.harness_mode = str(harness_mode or configured_harness_mode()).strip().casefold()
        self.task_mode = canonical_task_mode(task_mode) if task_mode else ""
        self.workflow_mode = workflow_mode
        self.jira_read_actions = frozenset(jira_read_actions or ())
        self.isolated_env: dict[str, str] | None = None
        self.additional_files: list[Path] = []
        self.additional_directories: list[Path] = []
        self.command_prefix: list[str] = []

    @property
    def capabilities(self) -> HarnessCapabilities:
        return capabilities_for_provider(
            "opencode",
            mode=self.harness_mode,
            sandbox=str(self.sandbox or "").strip().casefold() not in {"restricted", "read-only"},
            task_mode=self.task_mode,
        )

    def _agent_bin(self) -> str:
        path = find_opencode_bin()
        if path:
            return path
        raise RuntimeError("OpenCode CLI not found; install it with npm install -g opencode-ai")

    def _permission_config(self) -> dict[str, Any]:
        if self.harness_mode in {"unshackled", "dedicated_machine", "dedicated"}:
            # The provider is no longer the security boundary. The dedicated
            # Agent world supplies isolation, service identity, and the
            # publication gate, so OpenCode must be able to use its native
            # shell/edit/task/web tools without a command deny-list.
            bash_permissions: dict[str, Any] = {"*": "allow"}
            if "jira.workitem.get" in self.jira_read_actions:
                bash_permissions["twg jira workitem get *"] = "allow"
            if "jira.workitem.query" in self.jira_read_actions:
                bash_permissions["twg jira workitem query *"] = "allow"
            return {
                "*": "allow",
                "read": {
                    "*": "allow",
                    "**/.env*": "deny",
                    "**/*.pem": "deny",
                    "**/*.key": "deny",
                    "**/.ssh/**": "deny",
                },
                "glob": "allow",
                "grep": "allow",
                "edit": {
                    "*": "allow",
                    "**/.env*": "deny",
                    "**/*.pem": "deny",
                    "**/*.key": "deny",
                },
                "bash": bash_permissions,
                "task": "allow",
                "webfetch": "allow",
                "websearch": "allow",
                "question": "allow",
                "skill": "allow",
                "lsp": "allow",
                "external_directory": {
                    f"{path.expanduser().resolve()}/**": "allow"
                    for path in self.additional_directories
                    if path.is_dir()
                },
                "doom_loop": "deny",
            }
        if self.task_mode == "explore" and not self.workflow_mode:
            bash_permissions: dict[str, Any] = {
                "*": "deny",
                "rg *": "allow",
                "git status*": "allow",
                "git diff*": "allow",
                "git log*": "allow",
            }
            if "jira.workitem.get" in self.jira_read_actions:
                bash_permissions["twg jira workitem get *"] = "allow"
            if "jira.workitem.query" in self.jira_read_actions:
                bash_permissions["twg jira workitem query *"] = "allow"
            return {
                "*": "deny",
                "read": "allow",
                "glob": "allow",
                "grep": "allow",
                "edit": "deny",
                "bash": bash_permissions,
                "task": "deny",
                "webfetch": "allow",
                "websearch": "allow",
                "question": "allow",
                "skill": "allow",
                "lsp": "allow",
                "external_directory": {
                    f"{path.expanduser().resolve()}/**": "allow"
                    for path in self.additional_directories
                    if path.is_dir()
                },
                "doom_loop": "deny",
            }
        if self.workflow_mode:
            return {
                "*": "deny",
                "read": {
                    "*": "allow",
                    "**/.env*": "deny",
                    "**/*.pem": "deny",
                    "**/*.key": "deny",
                },
                "glob": "allow",
                "grep": "allow",
                "edit": {
                    "*": "allow",
                    "**/.env*": "deny",
                    "**/*.pem": "deny",
                    "**/*.key": "deny",
                },
                "bash": {
                    "*": "allow",
                    "rm *": "deny",
                    "sudo *": "deny",
                    "ssh *": "deny",
                    "scp *": "deny",
                    "curl *": "deny",
                    "wget *": "deny",
                    "git reset*": "deny",
                    "git clean*": "deny",
                    "git push*": "deny",
                },
                "task": "deny",
                "webfetch": "deny",
                "websearch": "deny",
                "question": "deny",
                "external_directory": {
                    f"{path.expanduser().resolve()}/**": "allow"
                    for path in self.additional_directories
                    if path.is_dir()
                },
                "doom_loop": "deny",
            }
        edit: Any = "deny"
        if self.agent_id == "mark":
            edit = {"*": "deny", "topics/**": "allow", "stories/**": "allow"}
        bash_permissions: dict[str, Any] = {
            "*": "deny",
            "rg *": "allow",
            "git status*": "allow",
            "git diff*": "allow",
            "git log*": "allow",
            "lumen *": "allow",
        }
        if "jira.workitem.get" in self.jira_read_actions:
            bash_permissions["twg jira workitem get *"] = "allow"
        if "jira.workitem.query" in self.jira_read_actions:
            bash_permissions["twg jira workitem query *"] = "allow"
        return {
            "*": "deny",
            "read": "allow",
            "glob": "allow",
            "grep": "allow",
            "edit": edit,
            "bash": bash_permissions,
            "task": "deny",
            "webfetch": "deny",
            "websearch": "deny",
            "question": "deny",
            "external_directory": {
                f"{path.expanduser().resolve()}/**": "allow"
                for path in self.additional_files
                if path.is_file()
            },
            "doom_loop": "deny",
        }

    def _config_content(self) -> str:
        model_id = _model_id(self.model)
        provider_id = _model_provider(self.model, self.base_url)
        model_options = {"reasoningEffort": "max"} if provider_id == "deepseek" else {}
        api_key = f"{{env:{self.api_key_env}}}" if self.api_key_env else "local"
        return json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "model": f"{provider_id}/{model_id}",
                "provider": {
                    provider_id: {
                        "npm": "@ai-sdk/openai-compatible",
                        "name": "Qwen (local)" if provider_id == "qwen" else "DeepSeek",
                        "options": {
                            "baseURL": self.base_url,
                            "apiKey": api_key,
                        },
                        "models": {
                            model_id: {
                                "name": model_id,
                                "options": model_options,
                            }
                        },
                    }
                },
                "mcp": {
                    "lumon": {
                        "type": "local",
                        "command": [sys.executable or "python3", "-m", "agents.runtime.native_tool_server"],
                        "enabled": True,
                    }
                },
                "permission": self._permission_config(),
            },
            ensure_ascii=False,
        )

    def _env(self) -> dict[str, str]:
        _load_lumen_dotenv()
        env = dict(self.isolated_env) if self.isolated_env is not None else {}
        if self.isolated_env is None:
            from agents.security.env import build_agent_env

            env = build_agent_env(agent_id=self.agent_id, project=self.project)
        if self.api_key_env:
            key = os.environ.get(self.api_key_env, "").strip()
            if not key and not is_local_opencode_provider(self.model, self.base_url):
                provider_id = _model_provider(self.model, self.base_url)
                raise RuntimeError(f"{provider_id} API key is not configured ({self.api_key_env}); add it to ~/.lumon/.env.local")
            if key:
                env[self.api_key_env] = key
        env["OPENCODE_CONFIG_CONTENT"] = self._config_content()
        env["LUMON_PROVIDER_SANDBOX"] = str(self.sandbox or "provider_default")
        home = Path(env.get("HOME") or Path.home()).expanduser()
        log_file = home / ".local" / "share" / "opencode" / "log" / "opencode.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.touch(exist_ok=True)
        return env

    def _ensure_workspace_context(self, workspace: Path) -> None:
        ensure_workspace_context(workspace, agent_id=self.agent_id)

    def run(
        self,
        *,
        workspace: Path,
        prompt: str,
        provider_session_id: str | None = None,
        trace: Any = None,
        obs: Any = None,
        on_event: Callable[[HarnessEvent], Any] | None = None,
    ) -> AgentRunResult:
        workspace = Path(workspace).expanduser().resolve()
        self._ensure_workspace_context(workspace)
        started = time.time()
        try:
            env = self._env()
            provider_id = _model_provider(self.model, self.base_url)
            command = [*self.command_prefix, self._agent_bin(), "run", "--log-level", "ERROR", "--format", "json", "--dir", str(workspace), "--model", f"{provider_id}/{_model_id(self.model)}"]
            if provider_session_id:
                command.extend(["--session", str(provider_session_id)])
            for path in self.additional_files:
                if path.is_file():
                    command.extend(["--file", str(path.expanduser().resolve())])
            command.append(prompt)
            if obs and trace:
                obs.emit(trace, "agent.run.started", workspace=str(workspace), resume=bool(provider_session_id), harness="opencode")
                obs.emit(trace, "agent.session.resumed" if provider_session_id else "agent.session.created", provider_session_id=provider_session_id or "")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(workspace),
                bufsize=1,
            )
        except Exception as exc:
            return AgentRunResult(text="", provider_session_id=provider_session_id or "", duration_ms=int((time.time() - started) * 1000), status="provider_error", error=str(exc)[:500])

        lines: list[str] = []
        stderr = ""
        timed_out = False
        assert process.stdout is not None
        try:
            while True:
                elapsed = time.time() - started
                if elapsed >= self.hard_timeout_seconds:
                    timed_out = True
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break
                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        lines.append(line)
                        self._emit_callback_event(line, on_event=on_event, sequence=len(lines) - 1)
                    elif process.poll() is not None:
                        break
                elif process.poll() is not None:
                    for rest in process.stdout.readlines():
                        lines.append(rest)
                        self._emit_callback_event(rest, on_event=on_event, sequence=len(lines) - 1)
                    break
            if process.stderr is not None:
                stderr = process.stderr.read().strip()
            if not timed_out and process.poll() is None:
                process.wait(timeout=5)
        except Exception as exc:
            try:
                process.kill()
            except OSError:
                pass
            return AgentRunResult(text="", provider_session_id=provider_session_id or "", duration_ms=int((time.time() - started) * 1000), status="failed", error=str(exc)[:500])

        parsed = parse_opencode_json_lines(lines)
        duration = int((time.time() - started) * 1000)
        if timed_out:
            # Text emitted before the hard timeout is an incomplete provider
            # stream, not a Feishu answer. Returning it as succeeded leaks
            # tool/planning progress through the legacy response sanitizer.
            parsed.text = ""
            parsed.error = f"agent hard timeout after {self.hard_timeout_seconds}s"
            parsed.status = "timed_out"
        if not parsed.text and parsed.status != "succeeded":
            if parsed.error:
                error = parsed.error
            elif stderr:
                error = stderr
            else:
                error = "OpenCode returned no usable response"
            parsed.error = error[:500]
            parsed.status = "timed_out" if timed_out else "failed"
        if obs and trace:
            event_name = "agent.result.completed" if parsed.status == "succeeded" else "agent.result.failed"
            obs.emit(
                trace,
                event_name,
                duration_ms=duration,
                tool_count=len(parsed.tool_events),
                provider_session_id=parsed.provider_session_id or provider_session_id or "",
                **({} if parsed.status == "succeeded" else {"error": parsed.error[:300], "level": "ERROR"}),
            )
        return AgentRunResult(
            text=parsed.text,
            provider_session_id=parsed.provider_session_id or provider_session_id or "",
            request_id=parsed.request_id,
            duration_ms=duration,
            tool_events=parsed.tool_events,
            status=parsed.status,
            error=parsed.error,
            raw_event_count=len(parsed.events),
            harness_events=normalize_provider_events(parsed.events, provider="opencode"),
        )

    @staticmethod
    def _emit_callback_event(
        line: str,
        *,
        on_event: Callable[[HarnessEvent], Any] | None,
        sequence: int,
    ) -> None:
        if on_event is None:
            return
        raw = str(line or "").strip()
        if not raw.startswith("{"):
            return
        try:
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return
        if not isinstance(value, dict):
            return
        event = from_provider_event(value, provider="opencode", sequence=sequence)
        if event is None:
            return
        try:
            on_event(event)
        except Exception:
            return
