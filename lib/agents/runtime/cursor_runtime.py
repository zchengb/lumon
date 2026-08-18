from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from agents.dylan.model_client import _load_lumen_dotenv
from agents.runtime.cursor_stream import AgentToolEvent, parse_stream_json_text
from agents.runtime.observability import Observability, TraceContext


@dataclass
class AgentRunResult:
    text: str
    provider_session_id: str
    request_id: str = ""
    duration_ms: int = 0
    tool_events: list[AgentToolEvent] = field(default_factory=list)
    status: str = "failed"
    error: str = ""
    raw_event_count: int = 0


class CursorAgentRuntime:
    supports_stateless = False
    supports_resume = True
    uses_isolated_env = True

    def __init__(
        self,
        *,
        model: str = "cursor-grok-4.5-medium",
        soft_timeout_seconds: int = 90,
        hard_timeout_seconds: int = 3600,
        sandbox: str = "enabled",
        force: bool = False,
        trust: bool = True,
        agent_id: str = "",
        project: str = "",
    ) -> None:
        self.model = model
        self.soft_timeout_seconds = soft_timeout_seconds
        self.hard_timeout_seconds = hard_timeout_seconds
        self.sandbox = sandbox
        self.force = force
        self.trust = trust
        self.agent_id = agent_id
        self.project = project
        self.isolated_env: Optional[dict[str, str]] = None
        self.additional_dirs: list[Path] = []

    def _agent_bin(self) -> str:
        for name in ("agent", "cursor-agent"):
            path = shutil.which(name)
            if path:
                return path
        raise RuntimeError("cursor agent CLI not found")

    def _env(self) -> dict[str, str]:
        if self.isolated_env is not None:
            return dict(self.isolated_env)
        from agents.security.env import build_agent_env

        _load_lumen_dotenv()
        return build_agent_env(agent_id=self.agent_id, project=self.project)

    def run(
        self,
        *,
        workspace: Path,
        prompt: str,
        provider_session_id: str | None = None,
        trace: TraceContext | None = None,
        obs: Observability | None = None,
    ) -> AgentRunResult:
        if self.sandbox != "enabled" or self.force:
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                status="security_error",
                error="SANDBOX_UNAVAILABLE",
            )
        agent_bin = self._agent_bin()
        workspace = Path(workspace).expanduser().resolve()
        args = [agent_bin]
        if provider_session_id:
            args.extend(["--resume", str(provider_session_id)])
        args.extend(
            [
                "--workspace",
                str(workspace),
                "--sandbox",
                "enabled",
                "-p",
                "--output-format",
                "stream-json",
                "--model",
                self.model,
            ]
        )
        for directory in self.additional_dirs:
            path = Path(directory).expanduser().resolve()
            if path.is_dir():
                args.extend(["--add-dir", str(path)])
        if self.trust:
            args.append("--trust")
        args.append(prompt)

        if obs and trace:
            event = "agent.session.resumed" if provider_session_id else "agent.session.created"
            obs.emit(trace, "agent.run.started", workspace=str(workspace), resume=bool(provider_session_id))
            obs.emit(trace, event, provider_session_id=provider_session_id or "")

        started = time.time()
        soft_emitted = False
        lines: list[str] = []
        stderr_chunks: list[str] = []
        run_env = self._env()
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=run_env,
            cwd=str(workspace),
            bufsize=1,
        )
        assert process.stdout is not None
        timed_out = False
        try:
            import select

            while True:
                elapsed = time.time() - started
                if not soft_emitted and elapsed >= self.soft_timeout_seconds:
                    soft_emitted = True
                    if obs and trace:
                        obs.emit(
                            trace,
                            "agent.progress",
                            duration_ms=int(elapsed * 1000),
                            message="Still checking the original failure path and related evidence.",
                        )
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
                        if obs and trace:
                            self._emit_line_events(line, obs=obs, trace=trace)
                    elif process.poll() is not None:
                        break
                elif process.poll() is not None:
                    for rest in process.stdout:
                        lines.append(rest)
                        if obs and trace:
                            self._emit_line_events(rest, obs=obs, trace=trace)
                    break
            if process.stderr is not None:
                stderr_chunks.append(process.stderr.read() or "")
            if not timed_out and process.poll() is None:
                process.wait(timeout=5)
        except Exception as exc:
            try:
                process.kill()
            except Exception:
                pass
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                duration_ms=int((time.time() - started) * 1000),
                status="failed",
                error=str(exc)[:500],
            )

        stdout = "".join(lines)
        stderr = "".join(stderr_chunks).strip()
        parsed = parse_stream_json_text(stdout)
        duration = parsed.duration_ms or int((time.time() - started) * 1000)

        if timed_out:
            if obs and trace:
                obs.emit(trace, "agent.result.failed", error=f"hard timeout after {self.hard_timeout_seconds}s", level="ERROR")
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                duration_ms=duration,
                status="timed_out",
                error=f"agent hard timeout after {self.hard_timeout_seconds}s",
            )

        combined_err = f"{stderr}\n{stdout}".lower()
        provider_error = _recent_cursor_provider_error(run_env, started)
        if provider_error:
            parsed.status = "failed"
            parsed.error = provider_error
        if any(
            token in combined_err
            for token in (
                "sandbox unavailable",
                "sandbox failed",
                "failed to initialize sandbox",
                "sandbox policy",
            )
        ):
            if obs and trace:
                obs.emit(trace, "security.sandbox.unavailable", level="ERROR", error=(stderr or stdout)[:300])
            return AgentRunResult(
                text="",
                provider_session_id=provider_session_id or "",
                duration_ms=duration,
                status="security_error",
                error="SANDBOX_UNAVAILABLE",
                raw_event_count=len(parsed.events),
            )

        code = process.returncode if process.returncode is not None else 1
        if code != 0 and parsed.status != "succeeded":
            err = parsed.error or stderr or (stdout or "agent failed")[:500]
            parsed.status = "failed"
            parsed.error = parsed.error or err
        elif parsed.status != "succeeded" and not parsed.text:
            err = stderr or stdout.strip()
            if err:
                parsed.error = (parsed.error or err)[:500]
            elif code != 0:
                parsed.error = parsed.error or f"agent exited {code} with empty stream-json"
            if "failed to reach the cursor api" in stderr.lower():
                parsed.error = stderr[:500]

        if obs and trace:
            if parsed.status == "succeeded":
                obs.emit(
                    trace,
                    "agent.result.completed",
                    duration_ms=duration,
                    tool_count=len(parsed.tool_events),
                    provider_session_id=parsed.provider_session_id,
                    request_id=parsed.request_id,
                )
            else:
                obs.emit(
                    trace,
                    "agent.result.failed",
                    error=parsed.error[:300],
                    level="ERROR",
                    provider_session_id=parsed.provider_session_id,
                )

        return AgentRunResult(
            text=parsed.text,
            provider_session_id=parsed.provider_session_id or (provider_session_id or ""),
            request_id=parsed.request_id,
            duration_ms=duration,
            tool_events=parsed.tool_events,
            status=parsed.status,
            error=parsed.error,
            raw_event_count=len(parsed.events),
        )

    def _emit_line_events(self, line: str, *, obs: Observability, trace: TraceContext) -> None:
        raw = line.strip()
        if not raw.startswith("{"):
            return
        try:
            event = json.loads(raw)
        except Exception:
            return
        if not isinstance(event, dict):
            return
        etype = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "")
        if etype == "tool_call":
            status = "started" if subtype == "started" else "completed" if subtype == "completed" else subtype or "event"
            tool = event.get("tool_call") if isinstance(event.get("tool_call"), dict) else {}
            tool_type = next(iter(tool.keys()), "") if tool else ""
            obs.emit(
                trace,
                f"agent.tool.{status}",
                tool_type=tool_type,
                call_id=str(event.get("call_id") or ""),
            )
        elif etype == "result":
            obs.emit(trace, "agent.final_response", subtype=subtype)


def _recent_cursor_provider_error(env: dict[str, str], started: float) -> str:
    """Read only the provider's recent error marker; never expose the log body."""
    tmpdir = str(env.get("TMPDIR") or os.environ.get("TMPDIR") or "").strip()
    if not tmpdir:
        return ""
    root = Path(tmpdir).expanduser()
    try:
        candidates = sorted(
            (path for path in root.glob("cursor-agent-logs-*/session-*.log") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:5]
    except OSError:
        return ""
    for path in candidates:
        try:
            if path.stat().st_mtime + 2 < started:
                continue
            body = path.read_text(encoding="utf-8", errors="replace")[-400_000:].lower()
        except OSError:
            continue
        if any(
            token in body
            for token in (
                "monthly usage limit",
                "request higher limits",
                "resource_exhausted",
                "error_rate_limited",
                "error_code=upgrade",
                'error_code":"upgrade',
            )
        ):
            return "Cursor monthly usage limit reached"
    return ""


def create_agent_runtime(
    *,
    provider: str,
    model: str,
    base_url: str = "",
    api_key_env: str = "",
    reasoning_effort: str = "",
    account_email: str = "",
    soft_timeout_seconds: int = 90,
    hard_timeout_seconds: int = 3600,
    sandbox: str = "enabled",
    force: bool = False,
    trust: bool = True,
    agent_id: str = "",
    project: str = "",
) -> Any:
    normalized = canonical_agent_provider(provider)
    if normalized == "codex":
        from agents.runtime.codex_runtime import CodexAgentRuntime

        return CodexAgentRuntime(
            model=model,
            reasoning_effort=reasoning_effort,
            account_email=account_email,
            soft_timeout_seconds=soft_timeout_seconds,
            hard_timeout_seconds=hard_timeout_seconds,
            sandbox=sandbox,
            force=force,
            trust=trust,
            agent_id=agent_id,
            project=project,
        )
    if normalized in {"opencode", "opencode_deepseek", "deepseek", "deepseek_api"}:
        from agents.runtime.opencode_runtime import OpenCodeAgentRuntime

        return OpenCodeAgentRuntime(
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            soft_timeout_seconds=soft_timeout_seconds,
            hard_timeout_seconds=hard_timeout_seconds,
            sandbox=sandbox,
            force=force,
            trust=trust,
            agent_id=agent_id,
            project=project,
        )
    if normalized in {"openai", "openai_compatible"}:
        from agents.runtime.openai_compatible import OpenAICompatibleAgentRuntime

        return OpenAICompatibleAgentRuntime(
            provider=normalized,
            model=model,
            base_url=base_url,
            api_key_env=api_key_env,
            soft_timeout_seconds=soft_timeout_seconds,
            hard_timeout_seconds=hard_timeout_seconds,
            sandbox=sandbox,
            force=force,
            trust=trust,
            agent_id=agent_id,
            project=project,
        )
    return CursorAgentRuntime(
        model=model,
        soft_timeout_seconds=soft_timeout_seconds,
        hard_timeout_seconds=hard_timeout_seconds,
        sandbox=sandbox,
        force=force,
        trust=trust,
        agent_id=agent_id,
        project=project,
    )


def canonical_agent_provider(provider: str) -> str:
    normalized = str(provider or "cursor").strip().casefold()
    if normalized in {"codex", "codex_cli", "codex-cli"}:
        return "codex"
    if normalized in {"deepseek", "deepseek_api", "opencode_deepseek"}:
        return "opencode"
    if normalized in {"cursor", "cursor-cli"}:
        return "cursor_cli"
    return normalized
