#!/usr/bin/env python3
"""Capture local, redacted Delivery agent invocation traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from delivery_workspace import load_story_context, read_json, workspace_lumen_dir, write_json
from format_scan_log import ScanLogFormatter, extract_assistant_text, tool_call_info, tool_result_status


SCHEMA_VERSION = "1.0"
DEFAULT_AGENT_IDLE_TIMEOUT_SECONDS = 3600
CAPTURE_MODES = {"off", "metadata", "full"}
SECRET_KEYS = re.compile(r"(?i)(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|cookie|session|client[_-]?secret|webhook[_-]?secret)")
ASSIGNMENT = re.compile(
    r"(?i)([\"']?\b(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|cookie|session|client[_-]?secret|webhook[_-]?secret)\b[\"']?\s*[:=]\s*)(?:Bearer\s+)?([^\s,;\"']+|\"[^\"]*\"|'[^']*')"
)
BEARER = re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+\-/=]+")
URL_PASSWORD = re.compile(r"(\b[a-z][a-z0-9+.-]*://[^\s:/@]+:)([^\s/@]+)(@)", re.I)
PRIVATE_KEY = re.compile(r"-----BEGIN [^-\n]*PRIVATE KEY-----.*?-----END [^-\n]*PRIVATE KEY-----", re.S)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def lumen_dir(workspace_root: Path) -> Path:
    """Accept either a project root or its already-resolved Lumen control plane."""
    if (workspace_root / "config" / "delivery.json").is_file() and (workspace_root / "results").is_dir():
        return workspace_root
    return workspace_lumen_dir(workspace_root)


def trace_config(workspace_root: Path) -> dict[str, Any]:
    path = lumen_dir(workspace_root) / "config" / "delivery.json"
    payload = read_json(path, {})
    observability = payload.get("observability") if isinstance(payload.get("observability"), dict) else {}
    configured = observability.get("agent_trace") if isinstance(observability.get("agent_trace"), dict) else {}
    mode = str(configured.get("capture_mode", "metadata")).strip().lower()
    if mode not in CAPTURE_MODES:
        raise ValueError(f"observability.agent_trace.capture_mode must be one of: {', '.join(sorted(CAPTURE_MODES))}")
    try:
        retention = int(configured.get("retention_days", 14))
    except (TypeError, ValueError) as exc:
        raise ValueError("observability.agent_trace.retention_days must be a positive integer") from exc
    if retention < 1:
        raise ValueError("observability.agent_trace.retention_days must be a positive integer")
    enabled = bool(configured.get("enabled", True)) and mode != "off"
    return {"enabled": enabled, "capture_mode": mode if enabled else "off", "retention_days": retention}


class Redactor:
    def __init__(self, workspace_root: Path):
        self.values: list[str] = []
        lumen = lumen_dir(workspace_root)
        for path in (lumen / ".env.common", lumen / ".env.local", workspace_root / ".env.common", workspace_root / ".env.local"):
            self._load_env(path)

    def _load_env(self, path: Path) -> None:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.removeprefix("export ").split("=", 1)
            value = value.strip().strip("\"'")
            if SECRET_KEYS.search(name) and value:
                self.values.append(value)
        self.values.sort(key=len, reverse=True)

    def text(self, value: Any) -> str:
        result = str(value)
        result = PRIVATE_KEY.sub("[REDACTED PRIVATE KEY]", result)
        result = BEARER.sub(r"\1[REDACTED]", result)
        result = ASSIGNMENT.sub(lambda m: f"{m.group(1)}[REDACTED]", result)
        result = URL_PASSWORD.sub(r"\1[REDACTED]\3", result)
        for secret in self.values:
            result = result.replace(secret, "[REDACTED]")
        return result

    def data(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: "[REDACTED]" if SECRET_KEYS.search(str(key)) else self.data(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.data(item) for item in value]
        return self.text(value) if isinstance(value, str) else value


def repository_state(path: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(["git", "-C", str(path), *args], text=True, capture_output=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    status: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for line in git("status", "--porcelain=v1", "-z", "--untracked-files=all").split("\0"):
        if not line:
            continue
        code, name = line[:2].strip() or "modified", line[3:]
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        status[name] = code
        target = path / name
        if target.is_file():
            try:
                hashes[name] = sha256(target.read_bytes())
            except OSError:
                pass
    return {"head": git("rev-parse", "HEAD"), "status": status, "hashes": hashes}


def changed_files(before: dict[str, dict[str, Any]], repos: list[Any]) -> dict[str, Any]:
    output: list[dict[str, Any]] = []
    heads: list[dict[str, str]] = []
    for repo in repos:
        root = Path(repo.worktree_path)
        old = before.get(repo.name, {})
        new = repository_state(root)
        heads.append({"repository": repo.name, "before_head": old.get("head", ""), "after_head": new.get("head", "")})
        names = sorted(set(old.get("status", {})) | set(new.get("status", {})))
        attributed = [name for name in names if old.get("status", {}).get(name) != new.get("status", {}).get(name) or old.get("hashes", {}).get(name) != new.get("hashes", {}).get(name)]
        committed: dict[str, str] = {}
        if old.get("head") and new.get("head") and old["head"] != new["head"]:
            committed_status = subprocess.run(["git", "-C", str(root), "diff", "--name-status", old["head"], new["head"]], text=True, capture_output=True, check=False).stdout
            for line in committed_status.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    committed[parts[-1]] = parts[0]
            attributed = sorted(set(attributed) | set(committed))
        diff_args = ["git", "-C", str(root), "diff", "--numstat"]
        if old.get("head") and new.get("head") and old["head"] != new["head"]:
            diff_args.extend([old["head"], new["head"]])
        diff_args.extend(["--", *attributed])
        numstat = subprocess.run(diff_args, text=True, capture_output=True, check=False).stdout
        counts = {line.split("\t", 2)[2]: line.split("\t", 2)[:2] for line in numstat.splitlines() if line.count("\t") >= 2}
        for name in attributed:
            additions, deletions = counts.get(name, ("0", "0"))
            code = new.get("status", {}).get(name) or committed.get(name, "D")
            if code == "??" and (root / name).is_file():
                try:
                    additions = str(len((root / name).read_text(encoding="utf-8", errors="replace").splitlines()))
                except OSError:
                    pass
            output.append({
                "repository": repo.name,
                "path": name,
                "status": "added" if "A" in code or code == "??" else "deleted" if "D" in code else "modified",
                "additions": int(additions) if additions.isdigit() else None,
                "deletions": int(deletions) if deletions.isdigit() else None,
            })
    return {"repositories": heads, "files": output}


def context_manifest(context: Any, remediation: bool, redactor: Redactor) -> dict[str, Any]:
    from compose_delivery_prompt import coding_guideline_path, delivery_prompts_dir

    prompts = delivery_prompts_dir(context)
    manifest_path = prompts / "manifest.json"
    manifest = read_json(manifest_path, {})
    paths: list[tuple[str, Path, bool]] = [("prompt_manifest", manifest_path, True)]
    for name in manifest.get("snippets", []):
        paths.append(("prompt_snippet", prompts / str(name), True))
    paths.extend([
        ("metadata", context.metadata_path, True),
        ("story", context.story_md, True),
        ("technical_plan", context.technical_plan, True),
        ("jira_context", lumen_dir(context.workspace_root) / "context" / context.story_dir.name / "jira-context.json", False),
        ("coding_guideline", coding_guideline_path(context), True),
    ])
    if remediation:
        paths.append(("remediation_evidence", lumen_dir(context.workspace_root) / "results" / "delivery-remediation.json", False))
    sources = []
    for order, (kind, path, required) in enumerate(paths, 1):
        try:
            content = redactor.text(path.read_text(encoding="utf-8"))
            sources.append({"type": kind, "path": str(path), "sha256": sha256(content), "characters": len(content), "included": True, "order": order})
        except OSError:
            sources.append({"type": kind, "path": str(path), "sha256": None, "characters": 0, "included": False, "reason": "source unavailable", "required": required, "order": order})
    return {"schema_version": SCHEMA_VERSION, "sources": sources}


def trace_root(workspace_root: Path, run_id: str) -> Path:
    return lumen_dir(workspace_root) / "results" / "agent-traces" / run_id


def cleanup_retention(workspace_root: Path, active_run: str, days: int) -> None:
    root = lumen_dir(workspace_root) / "results" / "agent-traces"
    cutoff = time.time() - days * 86400
    try:
        for path in root.iterdir():
            if path.is_dir() and path.name != active_run and path.stat().st_mtime < cutoff:
                shutil.rmtree(path)
    except OSError as exc:
        print(f"Warning: agent trace retention cleanup failed: {exc}", file=sys.stderr)


def update_trace_summary(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    path = root / "trace.json"
    trace = read_json(path, {"schema_version": SCHEMA_VERSION, "trace_id": root.name, "invocations": []})
    invocations = [item for item in trace.get("invocations", []) if item.get("invocation_id") != result["invocation_id"]]
    invocations.append({
        "invocation_id": result["invocation_id"], "stage": result["stage"], "attempt": result["attempt"],
        "status": result["status"], "duration_ms": result["duration_ms"], "tool_calls": result["tool_calls"],
        "files_changed": result["files_changed"], "trace_completeness": result["trace_completeness"],
    })
    trace.update({"invocations": invocations, "status": "available", "capture_mode": result["capture_mode"], "updated_at": utc_now()})
    write_json(path, trace)
    return trace


def merge_delivery_result(workspace_root: Path, trace: dict[str, Any]) -> None:
    path = lumen_dir(workspace_root) / "results" / "delivery-result.json"
    result = read_json(path, {})
    result["agent_trace"] = {
        "status": "available", "trace_id": trace["trace_id"],
        "path": str(Path("results") / "agent-traces" / trace["trace_id"]),
        "capture_mode": trace.get("capture_mode", "metadata"), "invocations": trace.get("invocations", []), "spans": trace.get("spans", []),
    }
    write_json(path, result)


class Normalizer:
    def __init__(self, trace_id: str, span_id: str, provider: str, redactor: Redactor, capture_mode: str, handle: Any):
        self.trace_id, self.span_id, self.provider = trace_id, span_id, provider
        self.redactor, self.capture_mode, self.handle = redactor, capture_mode, handle
        self.count = 0
        self.session_id = ""
        self.request_id = ""
        self.tool_started: dict[str, float] = {}
        self.tool_ids: list[str] = []
        self.tool_names: dict[str, str] = {}
        self.tool_summary: dict[str, dict[str, Any]] = {}
        self.parse_duration_ns = 0
        self.tool_calls = 0
        self.parse_warnings = 0
        self.first_event: float | None = None
        self.first_output: float | None = None
        self.final_output = ""
        self.provider_duration_ms = None
        self.provider_api_duration_ms = None

    def emit(self, kind: str, now: float, **fields: Any) -> None:
        self.count += 1
        event = {"schema_version": SCHEMA_VERSION, "trace_id": self.trace_id, "span_id": self.span_id, "event_id": f"evt-{self.count:06d}", "timestamp": utc_now(), "type": kind, "provider": self.provider, **fields}
        self.handle.write(json.dumps(self.redactor.data(event), ensure_ascii=False) + "\n")
        self.handle.flush()

    def parse(self, line: str, now: float) -> dict[str, Any] | None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.parse_warnings += 1
            self.emit("trace.parse.warning", now, message="Provider stdout contained invalid NDJSON")
            return None
        if not isinstance(event, dict):
            return None
        if self.first_event is None:
            self.first_event = now
        kind, subtype = event.get("type"), event.get("subtype")
        if kind == "system" and subtype == "init":
            self.session_id = str(event.get("session_id") or event.get("sessionId") or "")
            self.emit("agent.session.initialized", now, session_id=self.session_id, model=event.get("model"))
        elif kind == "assistant":
            visible = extract_assistant_text(event)
            if visible:
                self.first_output = self.first_output or now
                self.final_output = visible
                self.emit("agent.output.delta", now, text=visible if self.capture_mode == "full" else None)
        elif kind == "tool_call":
            tool = event.get("tool_call") or {}
            name, description = tool_call_info(tool)
            nested = next(iter(tool.values()), {}) if isinstance(tool, dict) and tool else {}
            explicit_id = event.get("tool_call_id") or event.get("id") or (nested.get("id") if isinstance(nested, dict) else "")
            call_id = str(explicit_id or (self.tool_ids[-1] if subtype == "completed" and self.tool_ids else f"tool-{self.tool_calls + 1:06d}"))
            if subtype == "started":
                self.tool_calls += 1
                self.tool_started[call_id] = now
                self.tool_ids.append(call_id)
                self.tool_names[call_id] = name
                summary = self.tool_summary.setdefault(name, {"name": name, "call_count": 0, "total_duration_ms": 0, "longest_duration_ms": 0, "failed_count": 0})
                summary["call_count"] += 1
                fields = {"tool_call_id": call_id, "tool": {"name": name, "summary": description}}
                if self.capture_mode == "full":
                    fields["tool"]["provider_payload"] = tool
                self.emit("agent.tool.started", now, **fields)
            elif subtype == "completed":
                started = self.tool_started.pop(call_id, None)
                name = self.tool_names.pop(call_id, name)
                if call_id in self.tool_ids:
                    self.tool_ids.remove(call_id)
                status = tool_result_status(tool)
                failed = bool(status and not status["ok"])
                duration_ms = round((now - started) * 1000) if started else None
                summary = self.tool_summary.setdefault(name, {"name": name, "call_count": 0, "total_duration_ms": 0, "longest_duration_ms": 0, "failed_count": 0})
                if duration_ms is not None:
                    summary["total_duration_ms"] += duration_ms
                    summary["longest_duration_ms"] = max(summary["longest_duration_ms"], duration_ms)
                if failed:
                    summary["failed_count"] += 1
                self.emit("agent.tool.failed" if failed else "agent.tool.completed", now, tool_call_id=call_id, tool={"name": name, "summary": description}, duration_ms=duration_ms, status="failed" if failed else "passed", error=status.get("detail") if failed else None)
        elif kind == "result":
            self.request_id = str(event.get("request_id") or event.get("requestId") or "")
            self.provider_duration_ms = event.get("duration_ms")
            self.provider_api_duration_ms = event.get("duration_api_ms") or event.get("api_duration_ms")
            visible = str(event.get("result") or "")
            if visible:
                self.first_output = self.first_output or now
                self.final_output = visible
            self.emit("agent.result.received", now, request_id=self.request_id, is_error=bool(event.get("is_error")), output=visible if self.capture_mode == "full" else None)
        return event


def run_agent(args: argparse.Namespace) -> int:
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    config = trace_config(workspace_root)
    prompt = sys.stdin.read()
    if not config["enabled"]:
        return subprocess.run([*args.command, prompt]).returncode

    context = load_story_context(Path(args.docs_dir), args.story)
    redactor = Redactor(workspace_root)
    root = trace_root(workspace_root, args.run_id)
    invocation_id = f"{args.stage}-{args.attempt:03d}"
    invocation = root / "agents" / invocation_id
    invocation.mkdir(parents=True, exist_ok=True)
    cleanup_retention(workspace_root, args.run_id, config["retention_days"])
    before = {repo.name: repository_state(Path(repo.worktree_path)) for repo in context.repos}
    redacted_prompt = redactor.text(prompt)
    manifest = context_manifest(context, args.stage == "remediation", redactor)
    manifest_text = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
    if config["capture_mode"] == "full":
        (invocation / "prompt.md").write_text(redacted_prompt, encoding="utf-8")
        write_json(invocation / "context-manifest.json", manifest)
    started_at, started_mono = utc_now(), time.monotonic()
    request = {
        "schema_version": SCHEMA_VERSION, "trace_id": args.run_id, "invocation_id": invocation_id,
        "stage": args.stage, "attempt": args.attempt, "provider": args.provider, "provider_executable": args.command[0],
        "model": args.model, "story": args.story, "output_format": args.output_format, "sandbox_mode": args.sandbox,
        "workspace": str(workspace_root), "repositories": [{"name": repo.name, "worktree": str(repo.worktree_path), "head": before[repo.name]["head"]} for repo in context.repos],
        "lumen_version": args.lumen_version, "provider_version": args.provider_version, "timeout_seconds": args.timeout,
        "prompt_sha256": sha256(redacted_prompt), "prompt_characters": len(redacted_prompt), "context_manifest_sha256": sha256(manifest_text),
        "capture_mode": config["capture_mode"], "started_at": started_at,
    }
    write_json(invocation / "request.json", request)
    events_handle = (invocation / "events.ndjson").open("w", encoding="utf-8")
    normalizer = Normalizer(args.run_id, invocation_id, args.provider, redactor, config["capture_mode"], events_handle)
    normalizer.emit("agent.process.started", started_mono)
    normalizer.emit("trace.redaction.applied", started_mono, sources=["prompt", "provider_events", "stdout", "stderr", "tool_payloads"])
    raw_events = (invocation / "provider-events.ndjson").open("w", encoding="utf-8") if config["capture_mode"] == "full" else None
    stdout_log = (invocation / "stdout.log").open("w", encoding="utf-8")
    stderr_log = (invocation / "stderr.log").open("w", encoding="utf-8")
    formatter = ScanLogFormatter() if args.output_format == "stream-json" else None
    process = subprocess.Popen([*args.command, prompt], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    process_started_mono = time.monotonic()
    last_activity_mono = process_started_mono
    last_activity_lock = threading.Lock()
    interrupted = False

    def terminate(signum: int, _frame: Any) -> None:
        nonlocal interrupted
        interrupted = True
        process.send_signal(signum)

    old_handlers = {sig: signal.signal(sig, terminate) for sig in (signal.SIGINT, signal.SIGTERM)}
    stdout_private_key = False
    stderr_private_key = False

    def redact_stream(raw: str, stderr: bool = False) -> str:
        nonlocal stdout_private_key, stderr_private_key
        active = stderr_private_key if stderr else stdout_private_key
        if active:
            if re.search(r"-----END [^-\n]*PRIVATE KEY-----", raw):
                if stderr: stderr_private_key = False
                else: stdout_private_key = False
            return ""
        if re.search(r"-----BEGIN [^-\n]*PRIVATE KEY-----", raw):
            if not re.search(r"-----END [^-\n]*PRIVATE KEY-----", raw):
                if stderr: stderr_private_key = True
                else: stdout_private_key = True
            return "[REDACTED PRIVATE KEY]\n"
        return redactor.text(raw)

    def mark_activity() -> None:
        nonlocal last_activity_mono
        with last_activity_lock:
            last_activity_mono = time.monotonic()

    def read_stdout() -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            mark_activity()
            clean = redact_stream(raw)
            if config["capture_mode"] == "full":
                stdout_log.write(clean); stdout_log.flush()
            if raw_events:
                raw_events.write(clean); raw_events.flush()
            if formatter:
                formatter.format_line(clean.rstrip("\n"))
            else:
                print(clean, end="", flush=True)
            parse_started = time.monotonic_ns()
            normalizer.parse(raw.rstrip("\n"), time.monotonic())
            normalizer.parse_duration_ns += time.monotonic_ns() - parse_started

    def read_stderr() -> None:
        assert process.stderr is not None
        for raw in process.stderr:
            mark_activity()
            clean = redact_stream(raw, stderr=True)
            if config["capture_mode"] == "full":
                stderr_log.write(clean); stderr_log.flush()
            print(clean, end="", file=sys.stderr, flush=True)
            normalizer.emit("agent.process.stderr", time.monotonic(), message=clean.rstrip() if config["capture_mode"] == "full" else None)

    threads = [threading.Thread(target=read_stdout), threading.Thread(target=read_stderr)]
    for thread in threads: thread.start()
    timed_out = False
    idle_timed_out = False
    while True:
        try:
            exit_code = process.wait(timeout=0.25)
            break
        except subprocess.TimeoutExpired:
            now = time.monotonic()
            with last_activity_lock:
                idle_for = now - last_activity_mono
            if args.idle_timeout and idle_for >= args.idle_timeout:
                idle_timed_out = True
                normalizer.emit("agent.process.idle_timeout", now, idle_timeout_seconds=args.idle_timeout, idle_duration_ms=round(idle_for * 1000))
                break
            if args.timeout and now - process_started_mono >= args.timeout:
                timed_out = True
                break
    if timed_out or idle_timed_out:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        exit_code = 124
    for thread in threads: thread.join()
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()
    ended_mono, ended_at = time.monotonic(), utc_now()
    for sig, handler in old_handlers.items(): signal.signal(sig, handler)
    changes = changed_files(before, context.repos)
    write_json(invocation / "changed-files.json", changes)
    if config["capture_mode"] == "full":
        (invocation / "final-output.md").write_text(redactor.text(normalizer.final_output), encoding="utf-8")
    status = "idle_timed_out" if idle_timed_out else "timed_out" if timed_out else "interrupted" if interrupted else "succeeded" if exit_code == 0 else "failed"
    normalizer.emit("agent.process.completed" if exit_code == 0 else "agent.process.interrupted" if interrupted else "agent.process.failed", ended_mono, exit_code=exit_code)
    result = {
        "schema_version": SCHEMA_VERSION, "trace_id": args.run_id, "invocation_id": invocation_id, "stage": args.stage, "attempt": args.attempt,
        "status": status, "exit_code": exit_code, "session_id": normalizer.session_id, "request_id": normalizer.request_id,
        "started_at": started_at, "ended_at": ended_at, "duration_ms": round((ended_mono - started_mono) * 1000),
        "provider_duration_ms": normalizer.provider_duration_ms, "provider_api_duration_ms": normalizer.provider_api_duration_ms,
        "process_startup_ms": round((process_started_mono - started_mono) * 1000),
        "result_parsing_ms": round(normalizer.parse_duration_ns / 1_000_000),
        "time_to_first_event_ms": round((normalizer.first_event - started_mono) * 1000) if normalizer.first_event else None,
        "time_to_first_output_ms": round((normalizer.first_output - started_mono) * 1000) if normalizer.first_output else None,
        "exit_reason": status, "idle_timeout_seconds": args.idle_timeout, "trace_completeness": "partial" if normalizer.parse_warnings else "full", "capture_mode": config["capture_mode"],
        "tool_calls": normalizer.tool_calls, "files_changed": len(changes["files"]),
        "tool_summary": sorted(normalizer.tool_summary.values(), key=lambda item: (-item["total_duration_ms"], item["name"])),
        "usage": {"requests": None, "input_tokens": None, "output_tokens": None, "cached_tokens": None, "reasoning_tokens": None, "estimated_cost": None, "source": "not_available"},
    }
    write_json(invocation / "result.json", result)
    for handle in (events_handle, raw_events, stdout_log, stderr_log):
        if handle: handle.close()
    trace = update_trace_summary(root, result)
    with (root / "spans.ndjson").open("a", encoding="utf-8") as spans:
        spans.write(json.dumps({"schema_version": SCHEMA_VERSION, "trace_id": args.run_id, "span_id": invocation_id, "parent_span_id": "delivery", "name": f"{args.stage}-agent", "started_at": started_at, "ended_at": ended_at, "duration_ms": result["duration_ms"], "status": status}, ensure_ascii=False) + "\n")
    merge_delivery_result(workspace_root, trace)
    return exit_code


def doctor(workspace_root: Path) -> int:
    try:
        config = trace_config(workspace_root)
        root = lumen_dir(workspace_root) / "results" / "agent-traces"
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write-test"
        probe.write_text("ok", encoding="utf-8"); probe.unlink()
        Redactor(workspace_root).text("password=secret")
        json.dumps({"schema_version": SCHEMA_VERSION})
        provider = shutil.which("agent")
        if provider:
            help_text = subprocess.run([provider, "--help"], text=True, capture_output=True, check=False).stdout
            if "stream-json" not in help_text:
                raise ValueError("Cursor CLI does not advertise stream-json output support")
        print(f"✓ Agent trace ready ({config['capture_mode']}, retention {config['retention_days']} days): {root}")
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"✗ Agent trace unavailable: {exc}", file=sys.stderr)
        return 1


def record_span(args: argparse.Namespace) -> int:
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    if not trace_config(workspace_root)["enabled"]:
        return 0
    ended_ns = time.monotonic_ns()
    duration_ms = max(0, round((ended_ns - args.started_ns) / 1_000_000))
    ended = datetime.now(timezone.utc)
    started = ended.timestamp() - duration_ms / 1000
    payload = {
        "schema_version": SCHEMA_VERSION, "trace_id": args.run_id, "span_id": args.span_id,
        "parent_span_id": args.parent_span_id or None, "name": args.name,
        "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "ended_at": ended.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "duration_ms": duration_ms, "status": args.status,
    }
    root = trace_root(workspace_root, args.run_id)
    root.mkdir(parents=True, exist_ok=True)
    with (root / "spans.ndjson").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    trace = read_json(root / "trace.json", {"schema_version": SCHEMA_VERSION, "trace_id": args.run_id, "invocations": []})
    spans = [item for item in trace.get("spans", []) if item.get("span_id") != args.span_id]
    spans.append({key: payload[key] for key in ("span_id", "parent_span_id", "name", "started_at", "ended_at", "duration_ms", "status")})
    trace["spans"] = spans
    write_json(root / "trace.json", trace)
    if trace.get("invocations") and (lumen_dir(workspace_root) / "results" / "delivery-result.json").is_file():
        merge_delivery_result(workspace_root, trace)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run")
    for name in ("workspace-root", "docs-dir", "story", "run-id", "stage", "provider", "model", "output-format", "sandbox", "lumen-version", "provider-version"):
        run.add_argument(f"--{name}", required=name in {"workspace-root", "docs-dir", "run-id", "stage"}, default="")
    run.add_argument("--attempt", type=int, default=1)
    run.add_argument("--timeout", type=int, default=3600)
    run.add_argument("--idle-timeout", type=int, default=DEFAULT_AGENT_IDLE_TIMEOUT_SECONDS)
    run.add_argument("command", nargs=argparse.REMAINDER)
    check = sub.add_parser("doctor"); check.add_argument("--workspace-root", required=True)
    span = sub.add_parser("span")
    span.add_argument("--workspace-root", required=True); span.add_argument("--run-id", required=True)
    span.add_argument("--span-id", required=True); span.add_argument("--name", required=True)
    span.add_argument("--started-ns", required=True, type=int); span.add_argument("--parent-span-id", default="delivery")
    span.add_argument("--status", choices=("succeeded", "failed"), default="succeeded")
    args = parser.parse_args()
    if args.action == "doctor": return doctor(Path(args.workspace_root).expanduser().resolve())
    if args.action == "span": return record_span(args)
    if args.command[:1] == ["--"]: args.command = args.command[1:]
    if not args.command: parser.error("provider command is required after --")
    return run_agent(args)


if __name__ == "__main__":
    raise SystemExit(main())
