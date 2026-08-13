from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from agents.dylan.model_client import _load_lumen_dotenv
from agents.runtime.cursor_runtime import AgentRunResult
from agents.runtime.cursor_stream import AgentToolEvent


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"


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
    value = str(model or "deepseek-v4-flash").strip()
    return value.split("/", 1)[1] if "/" in value else value


class OpenCodeAgentRuntime:
    """Persistent OpenCode Harness using DeepSeek as its configured provider."""

    supports_stateless = False
    supports_resume = True
    uses_isolated_env = True

    def __init__(
        self,
        *,
        model: str = "deepseek-v4-flash",
        base_url: str = "",
        api_key_env: str = "",
        soft_timeout_seconds: int = 90,
        hard_timeout_seconds: int = 300,
        sandbox: str = "enabled",
        force: bool = False,
        trust: bool = True,
        agent_id: str = "",
        project: str = "",
        workflow_mode: bool = False,
    ) -> None:
        self.model = model or "deepseek-v4-flash"
        self.base_url = base_url or DEFAULT_BASE_URL
        self.api_key_env = api_key_env or DEFAULT_API_KEY_ENV
        self.soft_timeout_seconds = soft_timeout_seconds
        self.hard_timeout_seconds = hard_timeout_seconds
        self.sandbox = sandbox
        self.force = force
        self.trust = trust
        self.agent_id = agent_id
        self.project = project
        self.workflow_mode = workflow_mode
        self.isolated_env: dict[str, str] | None = None
        self.additional_files: list[Path] = []
        self.additional_directories: list[Path] = []

    def _agent_bin(self) -> str:
        path = find_opencode_bin()
        if path:
            return path
        raise RuntimeError("OpenCode CLI not found; install it with npm install -g opencode-ai")

    def _permission_config(self) -> dict[str, Any]:
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
        return {
            "*": "deny",
            "read": "allow",
            "glob": "allow",
            "grep": "allow",
            "edit": edit,
            "bash": {
                "*": "deny",
                "rg *": "allow",
                "git status*": "allow",
                "git diff*": "allow",
                "git log*": "allow",
                "lumen *": "allow",
            },
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
        return json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "model": f"deepseek/{model_id}",
                "provider": {
                    "deepseek": {
                        "npm": "@ai-sdk/openai-compatible",
                        "name": "DeepSeek",
                        "options": {
                            "baseURL": self.base_url,
                            "apiKey": f"{{env:{self.api_key_env}}}",
                        },
                        "models": {model_id: {"name": model_id}},
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
        key = os.environ.get(self.api_key_env, "").strip()
        if not key:
            raise RuntimeError(f"DeepSeek API key is not configured ({self.api_key_env}); add it to ~/.lumon/.env.local")
        env[self.api_key_env] = key
        env["OPENCODE_CONFIG_CONTENT"] = self._config_content()
        home = Path(env.get("HOME") or Path.home()).expanduser()
        log_file = home / ".local" / "share" / "opencode" / "log" / "opencode.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.touch(exist_ok=True)
        return env

    def _ensure_workspace_context(self, workspace: Path) -> None:
        package_agents = Path(__file__).resolve().parents[1]
        target = workspace / ".lumon"
        target.mkdir(parents=True, exist_ok=True)
        for name in ("action-catalog.md", "protocol.md"):
            source = package_agents / name
            destination = target / name
            if source.is_file():
                shutil.copyfile(source, destination)

    def run(
        self,
        *,
        workspace: Path,
        prompt: str,
        provider_session_id: str | None = None,
        trace: Any = None,
        obs: Any = None,
    ) -> AgentRunResult:
        if self.sandbox != "enabled" or self.force:
            return AgentRunResult(text="", provider_session_id=provider_session_id or "", status="security_error", error="SANDBOX_UNAVAILABLE")
        workspace = Path(workspace).expanduser().resolve()
        self._ensure_workspace_context(workspace)
        started = time.time()
        try:
            env = self._env()
            command = [self._agent_bin(), "run", "--log-level", "ERROR", "--format", "json", "--dir", str(workspace), "--model", f"deepseek/{_model_id(self.model)}"]
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
                    elif process.poll() is not None:
                        break
                elif process.poll() is not None:
                    lines.extend(process.stdout.readlines())
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
        if timed_out and parsed.text:
            parsed.status = "succeeded"
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
        )
