#!/usr/bin/env python3
"""Run Auto Scan, Auto Delivery, or Auto Patch with the configured AI provider."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from agents.runtime.opencode_runtime import OpenCodeAgentRuntime
from agents.runtime.openai_compatible import chat_completion_messages, is_api_provider
from agents.runner.runner_env import build_runner_env


DEFAULT_MODEL = "cursor-grok-4.5-medium"
PROVIDERS = {"cursor_cli", "deepseek", "deepseek_api", "opencode", "opencode_deepseek", "openai", "openai_compatible"}
# Auto Scan may inspect many repositories before it can write its result. Keep
# a bounded budget, but leave enough turns for the configured workspace rather
# than failing halfway through normal evidence collection.
MAX_TOOL_LOOPS = 72
MAX_TOOL_OUTPUT = 20000


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def config_workspace(workspace: Path) -> Path:
    """Resolve a direct Lumon workspace or its parent project root."""
    workspace = workspace.expanduser().resolve()
    candidates = (workspace, *(workspace / name for name in ("lumon", "lumen", ".lumen")))
    return next((candidate for candidate in candidates if (candidate / "config").is_dir()), workspace)


def normalize_provider(value: str) -> str:
    provider = str(value or "cursor_cli").strip().casefold()
    if provider in {"cursor", "cursor-cli", "cursor_cli"}:
        return "cursor_cli"
    if provider in {"deepseek", "deepseek_api", "opencode", "opencode_deepseek"}:
        return "opencode"
    if provider in {"openai", "openai_compatible", "openai-compatible"}:
        return "openai_compatible"
    raise ValueError(f"Unsupported workflow AI provider: {provider}")


def resolve_config(
    workspace: Path,
    workflow: str,
    provider: str = "",
    model: str = "",
    base_url: str = "",
    api_key_env: str = "",
) -> dict[str, str]:
    config_root = config_workspace(workspace)
    common_execution = read_json(config_root / "config" / "common.json").get("execution")
    common_execution = common_execution if isinstance(common_execution, dict) else {}
    config_name = "common.json" if workflow == "auto_scan" else "delivery.json"
    workflow_execution = read_json(config_root / "config" / config_name).get("execution")
    workflow_execution = workflow_execution if isinstance(workflow_execution, dict) else {}
    execution = common_execution if any(common_execution.get(key) for key in ("provider", "model")) else workflow_execution
    prefix = "patch_" if workflow == "auto_patch" and execution is workflow_execution else ""
    selected_provider = provider or execution.get(f"{prefix}provider") or execution.get("provider") or "cursor_cli"
    normalized = normalize_provider(str(selected_provider))
    selected_model = model or execution.get(f"{prefix}model") or execution.get("model")
    if not selected_model:
        selected_model = (
            os.environ.get("CURSOR_AGENT_MODEL")
            if normalized == "cursor_cli"
            else "deepseek-v4-flash"
            if normalized == "opencode"
            else "gpt-4o-mini"
        )
    selected_base_url = base_url or execution.get(f"{prefix}base_url") or execution.get("base_url") or ""
    selected_key_env = api_key_env or execution.get(f"{prefix}api_key_env") or execution.get("api_key_env") or ""
    if not str(selected_model).strip():
        raise ValueError(f"No model configured for {workflow}")
    return {
        "provider": normalized,
        "model": str(selected_model).strip(),
        "base_url": str(selected_base_url or "").strip(),
        "api_key_env": str(selected_key_env or "").strip(),
    }


def emit(event: dict[str, Any], output_format: str) -> None:
    if output_format == "stream-json":
        print(json.dumps(event, ensure_ascii=False), flush=True)
    elif event.get("type") == "result":
        print(str(event.get("result") or ""), flush=True)


def redact(value: Any) -> str:
    result = str(value or "")
    for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CURSOR_API_KEY"):
        secret = os.environ.get(name, "")
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result[:MAX_TOOL_OUTPUT]


def trace_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    """Keep file contents out of the persisted execution trace."""
    safe = dict(result)
    if "content" in safe:
        safe["content"] = "[file content omitted from trace]"
    for key in ("output", "error"):
        if key in safe:
            safe[key] = redact(safe[key])
    return safe


def allowed_roots(workspace: Path) -> tuple[Path, ...]:
    roots = [workspace.parent.resolve(), workspace.resolve()]
    config_root = config_workspace(workspace)
    repositories = read_json(config_root / "config" / "repos.json").get("repositories")
    if isinstance(repositories, list):
        for repository in repositories:
            if isinstance(repository, dict) and repository.get("path"):
                roots.append(Path(str(repository["path"])).expanduser().resolve())
    return tuple(dict.fromkeys(roots))


def safe_path(value: str, roots: tuple[Path, ...], *, must_exist: bool = False) -> Path:
    candidate = Path(str(value or ".")).expanduser()
    if not candidate.is_absolute():
        candidate = roots[0] / candidate
    resolved = candidate.resolve()
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise PermissionError(f"path is outside the configured workspace: {resolved}")
    if must_exist and not resolved.exists():
        raise FileNotFoundError(str(resolved))
    return resolved


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": {"name": "list_directory", "description": "List files and directories", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 text file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}, "required": ["path"]}}},
        {"type": "function", "function": {"name": "write_file", "description": "Write a UTF-8 text file in an allowed repository", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
        {"type": "function", "function": {"name": "run_command", "description": "Run a bounded shell command in an allowed repository", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}, "timeout_seconds": {"type": "integer"}}, "required": ["command"]}}},
    ]


def run_tool(name: str, arguments: dict[str, Any], roots: tuple[Path, ...], agent_id: str, project: str) -> dict[str, Any]:
    if name == "list_directory":
        path = safe_path(str(arguments.get("path") or "."), roots, must_exist=True)
        if not path.is_dir():
            raise NotADirectoryError(str(path))
        entries = sorted(item.name + ("/" if item.is_dir() else "") for item in path.iterdir())[:300]
        return {"ok": True, "path": str(path), "entries": entries}
    if name == "read_file":
        path = safe_path(str(arguments.get("path") or ""), roots, must_exist=True)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        limit = max(1, min(int(arguments.get("max_bytes") or 30000), 100000))
        return {"ok": True, "path": str(path), "content": path.read_text(encoding="utf-8", errors="replace")[:limit]}
    if name == "write_file":
        path = safe_path(str(arguments.get("path") or ""), roots)
        content = str(arguments.get("content") or "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(path), "bytes": len(content.encode("utf-8"))}
    if name == "run_command":
        command = str(arguments.get("command") or "").strip()
        if not command:
            raise ValueError("command is required")
        cwd = safe_path(str(arguments.get("cwd") or str(roots[0])), roots, must_exist=True)
        if not cwd.is_dir():
            raise NotADirectoryError(str(cwd))
        timeout = max(1, min(int(arguments.get("timeout_seconds") or 120), 300))
        env = build_runner_env(agent_id=agent_id, project=project, source=os.environ)
        completed = subprocess.run(command, shell=True, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout, check=False)
        output = redact((completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else ""))
        return {"ok": completed.returncode == 0, "exit_code": completed.returncode, "cwd": str(cwd), "output": output}
    raise ValueError(f"Unknown workflow tool: {name}")


def run_cursor(config: dict[str, str], args: argparse.Namespace) -> int:
    if args.sandbox != "enabled":
        print("Auto workflow requires CURSOR_AGENT_SANDBOX=enabled; unsafe Cursor execution is disabled.", file=sys.stderr)
        return 78
    if not shutil_which("agent"):
        print("Cursor CLI 'agent' was not found in PATH.", file=sys.stderr)
        return 127
    command = ["agent", "--workspace", str(args.workspace), "--sandbox", args.sandbox, "--trust", "-p", "--output-format", args.output_format, "--model", config["model"]]
    if args.stream_partial_output:
        command.append("--stream-partial-output")
    if args.approve_mcps:
        command.append("--approve-mcps")
    command.append(args.prompt)
    env = build_runner_env(agent_id=args.agent_id, project=args.project, source=os.environ)
    env["CURSOR_AGENT_SANDBOX"] = args.sandbox
    return subprocess.run(command, env=env, check=False).returncode


def shutil_which(command: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def run_api(config: dict[str, str], args: argparse.Namespace) -> int:
    roots = allowed_roots(args.workspace)
    workflow = str(getattr(args, "workflow", "") or "")
    workflow_hint = {
        "auto_scan": (
            "For Auto Scan, batch related reads in one bounded command, do not reread evidence, "
            "and write the required scan-result.json as soon as the evidence is sufficient."
        ),
        "auto_delivery": "For Auto Delivery, inspect only the requested Story and its mapped repository scope.",
        "auto_patch": "For Auto Patch, inspect only the requested Jira card and its mapped repository scope.",
    }.get(workflow, "")
    messages: list[dict[str, Any]] = [{
        "role": "system",
        "content": (
            "You are the hands-on Lumon workflow agent. Work on the user's task directly: inspect the repositories, make the required changes, run focused checks, and report the concrete result. "
            "Do not stop at a plan or ask the user to create another request. Use the provided tools whenever repository evidence or changes are needed. "
            "Work efficiently within the bounded interaction budget: batch related reads, avoid repeating a successful tool call, and finish once the workflow output contract is satisfied. "
            f"{workflow_hint} "
            f"Allowed roots: {', '.join(str(root) for root in roots)}. Never read or write outside them."
        ),
    }, {"role": "user", "content": args.prompt}]
    started = time.monotonic()
    emit({"type": "system", "subtype": "init", "model": config["model"], "session_id": ""}, args.output_format)
    for _ in range(MAX_TOOL_LOOPS):
        try:
            body, request_id = chat_completion_messages(
                provider=config["provider"], model=config["model"], messages=messages,
                timeout=args.timeout, base_url=config["base_url"], api_key_env=config["api_key_env"], tools=tool_definitions(),
            )
        except Exception as exc:
            message = redact(exc)
            emit({"type": "result", "subtype": "error", "is_error": True, "result": message, "duration_ms": int((time.monotonic() - started) * 1000)}, args.output_format)
            return 1
        choices = body.get("choices")
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        assistant = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        tool_calls = assistant.get("tool_calls") if isinstance(assistant.get("tool_calls"), list) else []
        messages.append(assistant)
        if not tool_calls:
            content = assistant.get("content")
            if isinstance(content, list):
                content = "".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
            result = redact(content or "")
            if not result:
                result = "The workflow provider returned no usable answer."
            emit({"type": "assistant", "message": {"content": [{"type": "text", "text": result}]}}, args.output_format)
            emit({"type": "result", "subtype": "success", "request_id": request_id, "result": result, "duration_ms": int((time.monotonic() - started) * 1000)}, args.output_format)
            return 0
        for call in tool_calls:
            function = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = str(function.get("name") or "")
            call_id = str(call.get("id") or f"tool-{len(messages):04d}")
            try:
                arguments = json.loads(function.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be an object")
                safe_arguments = {key: ("[REDACTED]" if key == "content" else redact(value)) for key, value in arguments.items()}
                emit({"type": "tool_call", "subtype": "started", "tool_call_id": call_id, "tool_call": {"workflowToolCall": {"args": {"name": name, **safe_arguments}}}}, args.output_format)
                result = run_tool(name, arguments, roots, args.agent_id, args.project)
            except Exception as exc:
                result = {"ok": False, "error": redact(exc)}
            emit({"type": "tool_call", "subtype": "completed", "tool_call_id": call_id, "tool_call": {"workflowToolCall": {"args": {"name": name}, "result": trace_tool_result(result)}}}, args.output_format)
            messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, ensure_ascii=False)[:MAX_TOOL_OUTPUT]})
    result = f"Workflow agent reached the bounded interaction budget ({MAX_TOOL_LOOPS} rounds) before producing a final answer."
    emit({"type": "result", "subtype": "error", "is_error": True, "result": result, "duration_ms": int((time.monotonic() - started) * 1000)}, args.output_format)
    return 1


def run_opencode(config: dict[str, str], args: argparse.Namespace) -> int:
    roots = allowed_roots(args.workspace)
    runtime = OpenCodeAgentRuntime(
        model=config["model"],
        base_url=config["base_url"],
        api_key_env=config["api_key_env"],
        hard_timeout_seconds=args.timeout,
        sandbox=args.sandbox,
        agent_id=args.agent_id,
        project=args.project,
        workflow_mode=True,
    )
    runtime.additional_directories = list(roots)
    result = runtime.run(workspace=args.workspace, prompt=args.prompt)
    if result.status != "succeeded" or not result.text.strip():
        emit({"type": "result", "subtype": "error", "is_error": True, "result": redact(result.error or result.status)}, args.output_format)
        return 1
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": redact(result.text)}]}}, args.output_format)
    emit({"type": "result", "subtype": "success", "request_id": result.request_id, "session_id": result.provider_session_id, "result": redact(result.text), "duration_ms": result.duration_ms}, args.output_format)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--workflow", choices=("auto_scan", "auto_delivery", "auto_patch"), required=True)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--project", default="")
    parser.add_argument("--provider", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--sandbox", default="enabled")
    parser.add_argument("--output-format", default="stream-json")
    parser.add_argument("--stream-partial-output", action="store_true")
    parser.add_argument("--approve-mcps", action="store_true")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("prompt")
    args = parser.parse_args(argv)
    args.workspace = args.workspace.expanduser().resolve()
    try:
        config = resolve_config(args.workspace, args.workflow, args.provider, args.model, args.base_url, args.api_key_env)
        if config["provider"] == "opencode":
            return run_opencode(config, args)
        if is_api_provider(config["provider"]):
            return run_api(config, args)
        return run_cursor(config, args)
    except Exception as exc:
        print(redact(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
