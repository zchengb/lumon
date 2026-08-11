#!/usr/bin/env python3
"""Track and print detailed Lumen delivery progress."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from delivery_workspace import (
    delivery_result_path,
    delivery_results_dir,
    load_story_context,
    read_json,
    write_json,
)


PHASES = [
    ("preflight", "Preflight"),
    ("worktrees", "Feature worktrees"),
    ("jira_start", "JIRA IN DEV"),
    ("agent", "Implementation agent"),
    ("verification", "Verification"),
    ("finalize", "Commit, Push, And Pull Requests"),
    ("jira_done", "JIRA DEV DONE"),
    ("notify", "Notifications"),
    ("deployment", "Deployment"),
]

TERMINAL_DELIVERY_STATUSES = {"completed", "failed", "blocked"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def delivery_progress_path(workspace_root: Path) -> Path:
    return delivery_results_dir(workspace_root) / "delivery-progress.json"


def empty_progress() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": "",
        "delivery_status": "not_started",
        "current_phase": "",
        "current_step": "",
        "story_id": "",
        "story_path": "",
        "jira_key": "",
        "docs_dir": "",
        "workspace_root": "",
        "branch": "",
        "log_file": "",
        "started_at": "",
        "updated_at": "",
        "finished_at": "",
        "repositories": [],
        "phases": [],
        "verification": [],
        "jira": {},
        "feishu": {},
        "messages": [],
    }


def load_progress(workspace_root: Path) -> dict[str, Any]:
    path = delivery_progress_path(workspace_root)
    if not path.is_file():
        return empty_progress()
    payload = read_json(path, empty_progress())
    return payload if isinstance(payload, dict) else empty_progress()


def save_progress(workspace_root: Path, payload: dict[str, Any]) -> Path:
    payload["updated_at"] = utc_now()
    path = delivery_progress_path(workspace_root)
    write_json(path, payload)
    return path


def phase_index(payload: dict[str, Any], phase_id: str) -> Optional[int]:
    for index, phase in enumerate(payload.get("phases") or []):
        if phase.get("id") == phase_id:
            return index
    return None


def ensure_phases(payload: dict[str, Any]) -> None:
    existing = {phase.get("id") for phase in payload.get("phases") or [] if isinstance(phase, dict)}
    phases = list(payload.get("phases") or [])
    for phase_id, label in PHASES:
        if phase_id in existing:
            continue
        phases.append(
            {
                "id": phase_id,
                "label": label,
                "status": "pending",
                "started_at": "",
                "finished_at": "",
                "detail": "",
            }
        )
    payload["phases"] = phases


def set_phase(
    workspace_root: Path,
    phase_id: str,
    status: str,
    detail: str = "",
    current_step: str = "",
) -> dict[str, Any]:
    payload = load_progress(workspace_root)
    ensure_phases(payload)
    index = phase_index(payload, phase_id)
    if index is None:
        raise ValueError(f"Unknown phase: {phase_id}")

    phase = dict(payload["phases"][index])
    now = utc_now()
    attempts = [item for item in phase.get("attempts", []) if isinstance(item, dict)]
    if not attempts and phase.get("started_at"):
        attempts.append({"started_at": phase["started_at"], "finished_at": phase.get("finished_at", "")})
    if status == "in_progress" and phase.get("status") not in {"in_progress", "running"}:
        attempts.append({"started_at": now, "finished_at": ""})
        phase["started_at"] = attempts[0]["started_at"]
        phase["finished_at"] = ""
    if status in {"completed", "failed", "skipped"}:
        if not attempts:
            attempts.append({"started_at": phase.get("started_at") or now, "finished_at": now})
        elif not attempts[-1].get("finished_at"):
            attempts[-1]["finished_at"] = now
        phase["finished_at"] = now
    if attempts:
        phase["attempts"] = attempts
    phase["status"] = status
    if detail:
        phase["detail"] = detail
    payload["phases"][index] = phase
    payload["current_phase"] = phase_id
    if current_step:
        payload["current_step"] = current_step
    if status == "failed":
        payload["delivery_status"] = "failed"
    elif status == "in_progress":
        payload["delivery_status"] = "in_progress"
    return save_progress(workspace_root, payload) or payload


def init_progress(
    workspace_root: Path,
    docs_dir: Path,
    story_ref: str,
    run_id: str,
    log_file: str = "",
) -> dict[str, Any]:
    context = load_story_context(docs_dir, story_ref, validate_gates=False)
    payload = empty_progress()
    payload.update(
        {
            "run_id": run_id,
            "delivery_status": "in_progress",
            "story_id": context.metadata.get("storyId") or context.story_dir.name,
            "story_path": str(context.story_dir.relative_to(context.docs_dir)),
            "story_title": str(context.metadata.get("title") or "").strip(),
            "jira_key": context.metadata.get("jiraKey", ""),
            "docs_dir": str(context.docs_dir),
            "workspace_root": str(context.workspace_root),
            "branch": context.branch_name,
            "log_file": log_file,
            "started_at": utc_now(),
            "repositories": [
                {
                    "name": repo.name,
                    "source_path": str(repo.path),
                    "worktree_path": str(repo.worktree_path),
                    "branch": context.branch_name,
                }
                for repo in context.repos
            ],
        }
    )
    ensure_phases(payload)
    save_progress(workspace_root, payload)
    return payload


def enrich_progress(workspace_root: Path, prepare_payload: dict[str, Any]) -> None:
    payload = load_progress(workspace_root)
    repos = []
    for repo in prepare_payload.get("repos") or []:
        if not isinstance(repo, dict):
            continue
        repos.append(
            {
                "name": repo.get("name", ""),
                "source_path": repo.get("path", ""),
                "worktree_path": repo.get("worktree_path", ""),
                "branch": prepare_payload.get("branch_name", ""),
            }
        )
    if repos:
        payload["repositories"] = repos
    if prepare_payload.get("branch_name"):
        payload["branch"] = prepare_payload.get("branch_name")
    if prepare_payload.get("jira_key"):
        payload["jira_key"] = prepare_payload.get("jira_key")
    save_progress(workspace_root, payload)


def append_message(workspace_root: Path, message: str) -> None:
    payload = load_progress(workspace_root)
    messages = list(payload.get("messages") or [])
    messages.append({"at": utc_now(), "message": message})
    payload["messages"] = messages[-50:]
    save_progress(workspace_root, payload)


def append_verification(workspace_root: Path, item: dict[str, Any]) -> None:
    payload = load_progress(workspace_root)
    verification = list(payload.get("verification") or [])
    verification.append(item)
    payload["verification"] = verification
    payload["current_phase"] = "verification"
    payload["current_step"] = f"{item.get('repository', '')}: {item.get('label', item.get('id', ''))}"
    save_progress(workspace_root, payload)


def finish_progress(workspace_root: Path, delivery_status: str, detail: str = "") -> None:
    payload = load_progress(workspace_root)
    if detail:
        messages = list(payload.get("messages") or [])
        messages.append({"at": utc_now(), "message": detail})
        payload["messages"] = messages[-50:]
    payload["delivery_status"] = delivery_status
    if delivery_status in TERMINAL_DELIVERY_STATUSES:
        payload["finished_at"] = utc_now()
    if delivery_status in TERMINAL_DELIVERY_STATUSES:
        payload["current_phase"] = ""
        payload["current_step"] = ""
    save_progress(workspace_root, payload)


def report_payload(workspace_root: Path, progress: dict[str, Any]) -> dict[str, Any]:
    """Prefer the final delivery artifact when showing a completed run.

    Progress is updated continuously by the runner and can contain intermediate
    verification attempts. The final result is written by the delivery agent and
    finalizer, so it is the authoritative terminal status for the CLI report.
    """
    result = read_json(delivery_result_path(workspace_root), {})
    status = str(result.get("delivery_status", "")).strip()
    if status not in TERMINAL_DELIVERY_STATUSES and status != "awaiting_deploy":
        return progress

    payload = dict(progress)
    payload["delivery_status"] = status
    payload["finished_at"] = result.get("finished_at") or payload.get("finished_at", "")
    if status in TERMINAL_DELIVERY_STATUSES:
        payload["current_phase"] = ""
        payload["current_step"] = ""

    for key in ("story_id", "jira_key", "branch", "started_at"):
        if result.get(key):
            payload[key] = result[key]
    if isinstance(result.get("verification_results"), list):
        payload["verification"] = result["verification_results"]
    if isinstance(result.get("deployment"), dict):
        payload["deployment"] = result["deployment"]
    return payload


def status_icon(status: str) -> str:
    mapping = {
        "completed": "✓",
        "passed": "✓",
        "in_progress": "…",
        "failed": "✗",
        "skipped": "-",
        "pending": "○",
    }
    return mapping.get(status, "?")


def print_progress_report(workspace_root: Path) -> None:
    payload = report_payload(workspace_root, load_progress(workspace_root))
    if not payload.get("run_id"):
        print("No delivery progress found.")
        return

    print("")
    print("Lumen Delivery Progress")
    print("=======================")
    print(f"Run ID:      {payload.get('run_id', '')}")
    print(f"Status:      {payload.get('delivery_status', '')}")
    print(f"Story:       {payload.get('story_id', '')} ({payload.get('story_path', '')})")
    print(f"JIRA:        {payload.get('jira_key', '') or 'n/a'}")
    print(f"Branch:      {payload.get('branch', '') or 'n/a'}")
    print(f"Started:     {payload.get('started_at', '') or 'n/a'}")
    print(f"Updated:     {payload.get('updated_at', '') or 'n/a'}")
    if payload.get("finished_at"):
        print(f"Finished:    {payload.get('finished_at')}")
    if payload.get("current_phase"):
        print(f"Current:     {payload.get('current_phase')} / {payload.get('current_step', '')}")
    if payload.get("log_file"):
        print(f"Log:         {payload.get('log_file')}")
    print("")

    repos = payload.get("repositories") or []
    if repos:
        print("Repositories")
        print("------------")
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            print(f"- {repo.get('name', '')}")
            print(f"  worktree: {repo.get('worktree_path', '')}")
        print("")

    print("Phases")
    print("------")
    for phase in payload.get("phases") or []:
        if not isinstance(phase, dict):
            continue
        icon = status_icon(str(phase.get("status", "pending")))
        label = phase.get("label", phase.get("id", ""))
        detail = phase.get("detail", "")
        line = f"{icon} {label}"
        if detail:
            line += f" — {detail}"
        print(line)
    print("")

    verification = payload.get("verification") or []
    if verification:
        print("Verification")
        print("--------------")
        for item in verification:
            if not isinstance(item, dict):
                continue
            icon = status_icon(str(item.get("status", "")))
            repo = item.get("repository", "")
            label = item.get("label", item.get("id", ""))
            print(f"{icon} [{repo}] {label}")
            command = item.get("command", "")
            if command:
                print(f"    command: {command}")
            summary = item.get("summary", "")
            if summary and item.get("status") != "passed":
                print(f"    result: {summary}")
        print("")

    jira = payload.get("jira") or {}
    if jira:
        print(f"JIRA: {jira.get('status', '')} — {jira.get('detail', '')}")
    feishu = payload.get("feishu") or {}
    if feishu:
        print(f"Feishu: {feishu.get('status', '')} — {feishu.get('event', feishu.get('detail', ''))}")
    print("")


def update_notifications(workspace_root: Path, jira: dict[str, Any], feishu: dict[str, Any]) -> None:
    payload = load_progress(workspace_root)
    payload["jira"] = jira
    payload["feishu"] = feishu
    save_progress(workspace_root, payload)


def docker_available() -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if completed.returncode == 0:
        return True, "Docker is available"
    output = (completed.stderr or completed.stdout or "docker info failed").strip()
    return False, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Track Lumen delivery progress.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--workspace-root", required=True)
    init_parser.add_argument("--docs-dir", required=True)
    init_parser.add_argument("--story", default="")
    init_parser.add_argument("--run-id", required=True)
    init_parser.add_argument("--log-file", default="")

    phase_parser = subparsers.add_parser("phase")
    phase_parser.add_argument("--workspace-root", required=True)
    phase_parser.add_argument("phase_id")
    phase_parser.add_argument("status")
    phase_parser.add_argument("--detail", default="")
    phase_parser.add_argument("--step", default="")

    enrich_parser = subparsers.add_parser("enrich")
    enrich_parser.add_argument("--workspace-root", required=True)
    enrich_parser.add_argument("--prepare-json", required=True)

    message_parser = subparsers.add_parser("message")
    message_parser.add_argument("--workspace-root", required=True)
    message_parser.add_argument("text")

    finish_parser = subparsers.add_parser("finish")
    finish_parser.add_argument("--workspace-root", required=True)
    finish_parser.add_argument("status")
    finish_parser.add_argument("--detail", default="")

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--workspace-root", required=True)

    docker_parser = subparsers.add_parser("docker-check")
    docker_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "init":
        init_progress(
            Path(args.workspace_root),
            Path(args.docs_dir),
            args.story,
            args.run_id,
            args.log_file,
        )
        return 0

    if args.command == "phase":
        set_phase(
            Path(args.workspace_root),
            args.phase_id,
            args.status,
            args.detail,
            args.step,
        )
        return 0

    if args.command == "enrich":
        enrich_progress(Path(args.workspace_root), json.loads(args.prepare_json))
        return 0

    if args.command == "message":
        append_message(Path(args.workspace_root), args.text)
        return 0

    if args.command == "finish":
        finish_progress(Path(args.workspace_root), args.status, args.detail)
        return 0

    if args.command == "report":
        print_progress_report(Path(args.workspace_root))
        return 0

    if args.command == "docker-check":
        ok, detail = docker_available()
        payload = {"available": ok, "detail": detail}
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(detail)
        return 0 if ok else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
