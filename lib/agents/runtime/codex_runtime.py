from __future__ import annotations

import base64
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


DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_ACCOUNT_EMAIL = "kuoyio0820@gmail.com"
DEFAULT_CODEX_SANDBOX_MODE = "danger-full-access"
CODEX_DANGEROUS_ACCESS_FLAG = "--dangerously-bypass-approvals-and-sandbox"


def normalize_codex_sandbox_mode(value: str = "") -> str:
    """Return the Codex execution mode used by Lumon's agent runner.

    Lumon's generic runtime factory historically passed ``sandbox=enabled``
    to every provider. For Codex that value now means "use the configured
    Codex default", which is full host and network access unless the operator sets
    ``LUMON_CODEX_SANDBOX_MODE`` to a narrower mode.
    """

    requested = str(value or "").strip().casefold()
    if requested in {"", "enabled", "default"}:
        requested = os.environ.get("LUMON_CODEX_SANDBOX_MODE", DEFAULT_CODEX_SANDBOX_MODE).strip().casefold()
    aliases = {
        "off": "disabled",
        "none": "disabled",
        "unrestricted": "disabled",
        "full-access": "danger-full-access",
        "full": "danger-full-access",
        "dangerous": "disabled",
        "yolo": "disabled",
    }
    normalized = aliases.get(requested, requested)
    if normalized not in {"disabled", "danger-full-access", "workspace-write", "read-only"}:
        raise ValueError(f"unsupported Codex sandbox mode: {value}")
    return normalized


def find_codex_bin() -> str:
    path = shutil.which("codex")
    if path:
        return path
    candidates = (
        Path.home() / ".local" / "bin" / "codex",
        Path("/Applications/ChatGPT.app/Contents/Resources/codex"),
    )
    return next((str(candidate) for candidate in candidates if candidate.is_file() and os.access(candidate, os.X_OK)), "")


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    try:
        padding = "=" * ((4 - len(parts[1]) % 4) % 4)
        payload = base64.urlsafe_b64decode(parts[1] + padding)
        value = json.loads(payload.decode("utf-8"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def codex_account_email(codex_home: Path | None = None) -> str:
    home = Path(codex_home or "").expanduser() if codex_home else select_codex_home()
    path = home / "auth.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    tokens = payload.get("tokens") if isinstance(payload, dict) else {}
    token = tokens.get("id_token") if isinstance(tokens, dict) else ""
    claims = _decode_jwt_payload(str(token or ""))
    return str(claims.get("email") or claims.get("preferred_username") or "").strip().casefold()


def _codex_home_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("CODEX_HOME", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend((Path.home() / ".codex-three", Path.home() / ".codex"))
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def select_codex_home(expected_account_email: str = "") -> Path:
    candidates = _codex_home_candidates()
    expected = str(expected_account_email or "").strip().casefold()
    if expected:
        for candidate in candidates:
            if codex_account_email(candidate) == expected:
                return candidate
    configured = os.environ.get("CODEX_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return (Path.home() / ".codex").resolve()


def codex_account_status(expected_account_email: str = DEFAULT_ACCOUNT_EMAIL) -> dict[str, str | bool]:
    home = select_codex_home(expected_account_email)
    actual = codex_account_email(home)
    expected = str(expected_account_email or "").strip().casefold()
    return {
        "home": str(home),
        "email": actual,
        "expected_email": expected,
        "configured": bool(actual),
        "matches": bool(expected and actual and actual == expected),
    }


def codex_login_status(*, command: str = "", codex_home: Path | None = None) -> tuple[bool, str]:
    binary = command or find_codex_bin()
    if not binary:
        return False, "codex CLI not found"
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home or select_codex_home())
    try:
        completed = subprocess.run(
            [binary, "login", "status"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)[:160]
    detail = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode == 0 and "not logged in" not in detail.casefold(), detail[:160]


@dataclass
class CodexStreamResult:
    text: str = ""
    provider_session_id: str = ""
    request_id: str = ""
    status: str = "failed"
    error: str = ""
    tool_events: list[AgentToolEvent] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


def _item_text(item: dict[str, Any]) -> str:
    value = item.get("text") or item.get("content") or ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(
            str(part.get("text") or "")
            for part in value
            if isinstance(part, dict) and str(part.get("type") or "") in {"text", "output_text", "input_text"}
        )
    return str(value or "")


def parse_codex_json_lines(lines: Iterable[str]) -> CodexStreamResult:
    result = CodexStreamResult()
    text_parts: list[str] = []
    seen_message_ids: set[str] = set()
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
        event_type = str(event.get("type") or "").strip().casefold()
        session_id = str(event.get("thread_id") or event.get("threadId") or event.get("session_id") or "").strip()
        if session_id:
            result.provider_session_id = session_id
        request_id = event.get("turn_id") or event.get("turnId") or event.get("request_id") or event.get("requestId")
        if request_id:
            result.request_id = str(request_id)

        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        item_type = str(item.get("type") or "").strip().casefold()
        item_id = str(item.get("id") or "").strip()
        if item_type in {"agent_message", "assistant_message", "message"}:
            if not item_id or item_id not in seen_message_ids:
                if item_id:
                    seen_message_ids.add(item_id)
                value = _item_text(item).strip()
                if value:
                    text_parts.append(value)
            continue
        if item_type in {"command_execution", "file_change", "mcp_tool_call", "web_search", "computer_call"}:
            status = str(item.get("status") or event_type.removeprefix("item.") or "event")
            result.tool_events.append(
                AgentToolEvent(
                    tool_type=item_type[:80],
                    subtype=status[:80],
                    call_id=item_id[:120],
                    status="completed" if status in {"completed", "success", "succeeded"} else "started",
                    raw_summary=json.dumps({"type": item_type, "id": item_id}, ensure_ascii=False)[:240],
                )
            )
            continue
        if event_type == "error":
            result.error = str(event.get("message") or event.get("error") or "Codex returned an error")[:500]
            continue
        if event_type == "turn.failed":
            result.error = str(event.get("error") or event.get("message") or "Codex turn failed")[:500]
            continue
        if event_type in {"assistant", "message"}:
            message = event.get("message") if isinstance(event.get("message"), dict) else event
            value = _item_text(message)
            if value.strip():
                text_parts.append(value.strip())
        elif event.get("result") and isinstance(event.get("result"), str):
            text_parts.append(str(event["result"]).strip())

    result.text = "\n".join(part for part in text_parts if part).strip()
    if result.text and not result.error:
        result.status = "succeeded"
    elif result.error:
        result.status = "failed"
    return result


class CodexAgentRuntime:
    """Run Lumon turns through the installed Codex CLI and its ChatGPT login."""

    supports_stateless = False
    supports_resume = True
    uses_isolated_env = True

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        account_email: str = DEFAULT_ACCOUNT_EMAIL,
        output_schema: Path | None = None,
        soft_timeout_seconds: int = 90,
        hard_timeout_seconds: int = 3600,
        sandbox: str = "",
        force: bool = False,
        trust: bool = True,
        agent_id: str = "",
        project: str = "",
        harness_mode: str = "",
        task_mode: str = "",
    ) -> None:
        self.model = str(model or DEFAULT_MODEL).strip()
        self.reasoning_effort = str(reasoning_effort or DEFAULT_REASONING_EFFORT).strip().casefold()
        self.account_email = str(account_email or DEFAULT_ACCOUNT_EMAIL).strip().casefold()
        self.output_schema = Path(output_schema).expanduser().resolve() if output_schema else None
        self.soft_timeout_seconds = soft_timeout_seconds
        self.hard_timeout_seconds = hard_timeout_seconds
        self.sandbox = normalize_codex_sandbox_mode(sandbox)
        self.force = force
        self.trust = trust
        self.agent_id = agent_id
        self.project = project
        self.harness_mode = str(harness_mode or configured_harness_mode()).strip().casefold()
        self.task_mode = canonical_task_mode(task_mode) if task_mode else ""
        self.isolated_env: dict[str, str] | None = None
        self.additional_dirs: list[Path] = []
        self.additional_directories = self.additional_dirs
        self.command_prefix: list[str] = []

    @property
    def capabilities(self) -> HarnessCapabilities:
        return capabilities_for_provider(
            "codex",
            mode=self.harness_mode,
            sandbox=self.sandbox != "read-only",
            task_mode=self.task_mode,
        )

    def _codex_home(self) -> Path:
        return select_codex_home(self.account_email)

    def _env(self) -> dict[str, str]:
        if self.isolated_env is not None:
            env = dict(self.isolated_env)
            # An Agent World must not resolve the operator's personal
            # ~/.codex directory. Explicit provisioning writes the service
            # identity's home instead.
            codex_home = Path(env.get("HOME") or Path.home()).expanduser() / ".codex"
        else:
            from agents.security.env import build_agent_env

            _load_lumen_dotenv()
            env = build_agent_env(agent_id=self.agent_id, project=self.project)
            codex_home = self._codex_home()
        env["CODEX_HOME"] = str(codex_home)
        return env

    def _agent_bin(self) -> str:
        binary = find_codex_bin()
        if not binary:
            raise RuntimeError("codex CLI not found")
        return binary

    def _ensure_workspace_context(self, workspace: Path) -> None:
        ensure_workspace_context(workspace, agent_id=self.agent_id)

    def _execution_args(self, *, resume: bool) -> list[str]:
        if self.sandbox == "disabled":
            return [CODEX_DANGEROUS_ACCESS_FLAG]
        if self.sandbox == "danger-full-access":
            if resume:
                return ["-c", 'sandbox_mode="danger-full-access"']
            return ["--sandbox", "danger-full-access"]
        if resume:
            return ["-c", f'sandbox_mode="{self.sandbox}"']
        return ["--sandbox", self.sandbox]

    @staticmethod
    def _native_mcp_config_args(workspace: Path) -> list[str]:
        """Register Lumon's MCP server in the provider-native Codex config."""

        manifest = Path(workspace).expanduser().resolve() / ".lumon" / "native-tools.json"
        python_executable = str(sys.executable or "python3")
        return [
            "-c",
            f"mcp_servers.lumon.command={json.dumps(python_executable)}",
            "-c",
            'mcp_servers.lumon.args=["-m", "agents.runtime.native_tool_server"]',
            "-c",
            f"mcp_servers.lumon.env.LUMON_NATIVE_TOOL_MANIFEST={json.dumps(str(manifest))}",
        ]

    def _command(self, workspace: Path, prompt: str, provider_session_id: str | None) -> list[str]:
        binary = self._agent_bin()
        config = f'model_reasoning_effort="{self.reasoning_effort}"'
        if provider_session_id:
            command = [
                binary,
                "--ask-for-approval",
                "never",
                "exec",
                "resume",
                str(provider_session_id),
                "--json",
                "--model",
                self.model,
                "-c",
                config,
            ]
            command.extend(self._native_mcp_config_args(workspace))
            command.extend(self._execution_args(resume=True))
            if self.output_schema:
                command.extend(["--output-schema", str(self.output_schema)])
            command.append(prompt)
            return command
        command = [
            binary,
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
            "--model",
            self.model,
            "-c",
            config,
            *self._native_mcp_config_args(workspace),
            *self._execution_args(resume=False),
            "--cd",
            str(workspace),
            "--color",
            "never",
        ]
        if self.output_schema:
            command.extend(["--output-schema", str(self.output_schema)])
        for directory in [*self.additional_dirs, *getattr(self, "additional_directories", [])]:
            path = Path(directory).expanduser().resolve()
            if path.is_dir() and str(path) != str(workspace):
                command.extend(["--add-dir", str(path)])
        command.append(prompt)
        return command

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
        account = codex_account_status(self.account_email)
        if not account["matches"]:
            actual = str(account.get("email") or "not logged in")
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                status="provider_error",
                error=f"CODEX_ACCOUNT_MISMATCH expected {self.account_email}, got {actual}",
            )
        try:
            command = [*self.command_prefix, *self._command(workspace, prompt, provider_session_id)]
            env = self._env()
        except Exception as exc:
            return AgentRunResult(text="", provider_session_id=provider_session_id or "", status="provider_error", error=str(exc)[:500])

        started = time.time()
        if obs and trace:
            obs.emit(trace, "agent.run.started", workspace=str(workspace), resume=bool(provider_session_id), harness="codex")
            obs.emit(trace, "agent.session.resumed" if provider_session_id else "agent.session.created", provider_session_id=provider_session_id or "")
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
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
        timed_out = False
        assert process.stdout is not None
        try:
            soft_emitted = False
            while True:
                elapsed = time.time() - started
                if not soft_emitted and elapsed >= self.soft_timeout_seconds:
                    soft_emitted = True
                    if obs and trace:
                        obs.emit(trace, "agent.progress", duration_ms=int(elapsed * 1000), message="Codex is still working through the workspace evidence.")
                        obs.emit(trace, "agent.run.long_running", duration_ms=int(elapsed * 1000))
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
                        if obs and trace:
                            self._emit_line_events(line, obs=obs, trace=trace)
                    elif process.poll() is not None:
                        break
                elif process.poll() is not None:
                    for rest in process.stdout.readlines():
                        lines.append(rest)
                        self._emit_callback_event(rest, on_event=on_event, sequence=len(lines) - 1)
                    break
            stderr = process.stderr.read().strip() if process.stderr is not None else ""
            if not timed_out and process.poll() is None:
                process.wait(timeout=5)
        except Exception as exc:
            try:
                process.kill()
            except OSError:
                pass
            return AgentRunResult(text="", provider_session_id=provider_session_id or "", duration_ms=int((time.time() - started) * 1000), status="failed", error=str(exc)[:500])

        parsed = parse_codex_json_lines(lines)
        duration = int((time.time() - started) * 1000)
        if timed_out:
            parsed.text = ""
            parsed.status = "timed_out"
            parsed.error = f"agent hard timeout after {self.hard_timeout_seconds}s"
        elif process.returncode != 0 and parsed.status != "succeeded":
            parsed.status = "failed"
            parsed.error = (parsed.error or stderr or "Codex returned no usable response")[:500]
        elif parsed.status != "succeeded" and not parsed.text:
            parsed.error = (parsed.error or stderr or "Codex returned no usable response")[:500]
            parsed.status = "failed"
        if obs and trace:
            if parsed.status == "succeeded":
                obs.emit(trace, "agent.result.completed", duration_ms=duration, tool_count=len(parsed.tool_events), provider_session_id=parsed.provider_session_id)
            else:
                obs.emit(trace, "agent.result.failed", error=parsed.error[:300], level="ERROR", provider_session_id=parsed.provider_session_id)
        return AgentRunResult(
            text=parsed.text,
            provider_session_id=parsed.provider_session_id or (provider_session_id or ""),
            request_id=parsed.request_id,
            duration_ms=duration,
            tool_events=parsed.tool_events,
            status=parsed.status,
            error=parsed.error,
            raw_event_count=len(parsed.events),
            harness_events=normalize_provider_events(parsed.events, provider="codex"),
        )

    def _emit_line_events(self, line: str, *, obs: Any, trace: Any) -> None:
        try:
            event = json.loads(line)
        except (TypeError, ValueError):
            return
        if not isinstance(event, dict):
            return
        event_type = str(event.get("type") or "")
        if event_type.startswith("item."):
            item = event.get("item") if isinstance(event.get("item"), dict) else {}
            item_type = str(item.get("type") or "")
            if item_type:
                obs.emit(trace, f"agent.tool.{event_type.removeprefix('item.')}", tool_type=item_type[:80], call_id=str(item.get("id") or "")[:120])
        elif event_type == "turn.completed":
            obs.emit(trace, "agent.final_response", subtype=event_type)

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
        event = from_provider_event(value, provider="codex", sequence=sequence)
        if event is None:
            return
        try:
            on_event(event)
        except Exception:
            return
