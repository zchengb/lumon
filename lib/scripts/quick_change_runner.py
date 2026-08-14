#!/usr/bin/env python3
"""Run one small, explicitly scoped change without Story/plan gates."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from agents.runner.runner_env import build_runner_env
from delivery_progress import docker_available
from delivery_workspace import (
    delivery_worktrees_dir,
    discover_git_repos,
    load_delivery_config,
    load_workspace_config,
    normalize_verification_settings,
    repo_path_for_name,
    repos_registry,
    resolve_docs_dir,
    resolve_repo_default_branch,
    slugify,
    workspace_lumen_dir,
    write_json,
)
from git_publish import merge_pr, open_pr_with_retry, push_default_branch, run_git, commit_changes
from run_delivery_verification import docker_policy, run_step, verification_steps
from sync_delivery_docs import lumen_commit_subject


VERSION_RE = re.compile(r"\b(version|upgrade|bump)\b|版本|升级|更新版本", re.IGNORECASE)
PUBLISH_MODES = {"none", "pr", "merge", "direct"}


class QuickChangeBlocked(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_target_files(values: Any) -> list[str]:
    if isinstance(values, str):
        raw = values.replace(",", "\n").splitlines()
    elif isinstance(values, (list, tuple)):
        raw = list(values)
    else:
        raw = []
    files: list[str] = []
    for item in raw:
        value = str(item or "").strip().replace("\\", "/")
        if not value or value in files:
            continue
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
            raise QuickChangeBlocked(f"invalid target file: {value}")
        files.append(path.as_posix())
    if not files:
        raise QuickChangeBlocked("at least one target file is required")
    if len(files) > 8:
        raise QuickChangeBlocked("quick change allows at most 8 target files")
    return files


def is_version_change(request: str, change_type: str) -> bool:
    return str(change_type or "").casefold() in {"version", "version_bump", "upgrade_version"} or bool(VERSION_RE.search(request))


def configured_publish_mode(config: dict[str, Any]) -> str:
    publish = config.get("publish") if isinstance(config.get("publish"), dict) else {}
    quick = publish.get("quick_change") if isinstance(publish.get("quick_change"), dict) else {}
    mode = str(quick.get("mode") or publish.get("mode") or "pr").strip().casefold() or "pr"
    if mode not in PUBLISH_MODES:
        raise QuickChangeBlocked("publish mode must be none, pr, merge, or direct")
    return mode


def _git_text(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    return (result.stderr or result.stdout or fallback).strip()


def _result_path(workspace_root: Path, run_id: str) -> Path:
    return workspace_lumen_dir(workspace_root) / "results" / "quick-changes" / f"{run_id}.json"


def _log_path(workspace_root: Path, run_id: str) -> Path:
    return workspace_lumen_dir(workspace_root) / "logs" / "quick-change" / f"{run_id}.log"


def _lock_path(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "locks" / "delivery-run"


def _set_result(path: Path, result: dict[str, Any], **updates: Any) -> None:
    result.update(updates)
    result["updated_at"] = utc_now()
    write_json(path, result)


def _remove_worktree(repo: Path, worktree: Path) -> None:
    run_git(repo, "worktree", "remove", "--force", str(worktree))


def _run_agent(worktree: Path, prompt: str, log_path: Path, model: str, repository: str) -> None:
    sandbox = os.environ.get("CURSOR_AGENT_SANDBOX", "enabled").strip().casefold()
    if sandbox != "enabled":
        raise QuickChangeBlocked("secure Agent sandbox is required")
    args = [
        os.environ.get("LUMEN_AGENT_BIN", "agent"),
        "--workspace",
        str(worktree),
        "--sandbox",
        "enabled",
        "--trust",
        "-p",
        "--output-format",
        os.environ.get("CURSOR_AGENT_OUTPUT_FORMAT", "stream-json"),
        "--model",
        model,
        prompt,
    ]
    env = build_runner_env(agent_id="mark", project=repository, source=os.environ)
    env["CURSOR_AGENT_SANDBOX"] = "enabled"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(args, cwd=str(worktree), env=env, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"quick-change Agent exited with code {completed.returncode}; inspect {log_path}")


def _verify(
    *,
    workspace_root: Path,
    worktree: Path,
    repository: str,
    delivery_config: dict[str, Any],
) -> list[dict[str, Any]]:
    verification = delivery_config.get("verification") if isinstance(delivery_config.get("verification"), dict) else {}
    if verification.get("auto_run_after_agent") is False:
        return [{"repository": repository, "id": "verification", "status": "skipped", "summary": "Disabled by delivery configuration"}]
    registry_entry = repos_registry(workspace_root).get(repository, {})
    configured_steps = verification.get("steps", {}).get(repository) if isinstance(verification.get("steps"), dict) else []
    settings = normalize_verification_settings(
        registry_entry.get("verification") if isinstance(registry_entry, dict) else {},
        has_custom_commands=isinstance(configured_steps, list) and bool(configured_steps),
    )
    if settings["mode"] == "skip":
        return [{"repository": repository, "id": "verification", "status": "skipped", "summary": "Skipped by repository configuration"}]
    steps = verification_steps(
        delivery_config,
        worktree,
        mode=settings["mode"],
        compile_enabled=settings["compile"],
        tests_enabled=settings["tests"],
    )
    if not steps:
        return [{"repository": repository, "id": "verification", "status": "skipped", "summary": "No automatic verification profile"}]
    policy = docker_policy(delivery_config)
    docker_ok, docker_detail = docker_available()
    results: list[dict[str, Any]] = []
    for step in steps:
        item = run_step(worktree, step, policy, docker_ok, docker_detail)
        item["repository"] = repository
        results.append(item)
    return results


def _change_scope(worktree: Path, target_files: list[str], target_version: str, version_change: bool) -> list[str]:
    from git_publish import changed_files

    changed = changed_files(worktree)
    allowed = set(target_files)
    outside = [item for item in changed if item not in allowed]
    if outside:
        raise QuickChangeBlocked(f"Agent changed files outside the approved scope: {', '.join(outside)}")
    if not changed:
        raise QuickChangeBlocked("Agent made no changes")
    if version_change and target_version:
        found = any(target_version in (worktree / item).read_text(encoding="utf-8", errors="ignore") for item in changed)
        if not found:
            raise QuickChangeBlocked("target version was not found in the changed target files")
    return changed


def run(args: argparse.Namespace) -> int:
    docs_dir = resolve_docs_dir(Path(args.docs_dir))
    workspace_root, workspace_config = load_workspace_config(docs_dir)
    delivery_config = load_delivery_config(docs_dir, workspace_root)
    run_id = str(args.run_id or f"quick-{uuid.uuid4().hex[:12]}").strip()
    repository = str(args.repository or "").strip()
    request = str(args.request or "").strip()
    change_type = str(args.change_type or "small_change").strip()
    target_version = str(args.target_version or "").strip()
    target_files = normalize_target_files(args.target_file)
    if not repository:
        raise QuickChangeBlocked("repository is required")
    if Path(repository).name != repository or repository in {".", ".."}:
        raise QuickChangeBlocked("repository must be a registered repository name")
    if not request:
        raise QuickChangeBlocked("request is required")
    if len(request) > 1200:
        raise QuickChangeBlocked("quick-change request is too long")
    if is_version_change(request, change_type) and not target_version:
        raise QuickChangeBlocked("target version is required for a version change")
    if len(target_version) > 100:
        raise QuickChangeBlocked("target version is too long")

    discovered = discover_git_repos(workspace_root, workspace_config)
    configured_names = {
        str(item.get("name") or "").strip()
        for item in (workspace_config.get("repositories") or [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    if repository not in discovered and repository not in configured_names:
        raise QuickChangeBlocked(f"repository is not registered: {repository}")
    source_repo = repo_path_for_name(repository, workspace_root, workspace_config, discovered)
    if source_repo is None:
        raise QuickChangeBlocked(f"repository not found: {repository}")
    registry_entry = repos_registry(workspace_root).get(repository, {})
    automation = registry_entry.get("automation") if isinstance(registry_entry.get("automation"), dict) else {}
    delivery_automation = automation.get("delivery") if isinstance(automation.get("delivery"), dict) else {}
    quick_automation = automation.get("quick_change") if isinstance(automation.get("quick_change"), dict) else {}
    if delivery_automation.get("enabled") is False or quick_automation.get("enabled") is False:
        raise QuickChangeBlocked(f"repository '{repository}' is not authorized for quick changes")

    source_repo = source_repo.resolve()
    for target in target_files:
        raw_candidate = source_repo / target
        candidate = raw_candidate.resolve()
        if raw_candidate.is_symlink() or source_repo not in candidate.parents or not candidate.is_file():
            raise QuickChangeBlocked(f"target file is not an existing repository file: {target}")

    result_path = _result_path(workspace_root, run_id)
    log_path = _log_path(workspace_root, run_id)
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "kind": "quick_change",
        "run_id": run_id,
        "status": "running",
        "delivery_status": "running",
        "repository": repository,
        "target_files": target_files,
        "request": request,
        "change_type": change_type,
        "target_version": target_version,
        "docs_dir": str(docs_dir),
        "workspace_root": str(workspace_root),
        "log_file": str(log_path),
        "started_at": utc_now(),
        "actor": os.environ.get("LUMEN_QUICK_CHANGE_ACTOR", ""),
        "source_message_id": os.environ.get("LUMEN_QUICK_CHANGE_SOURCE_MESSAGE_ID", ""),
        "chat_id": os.environ.get("LUMEN_QUICK_CHANGE_CHAT_ID", ""),
        "thread_id": os.environ.get("LUMEN_QUICK_CHANGE_THREAD_ID", ""),
        "project_slug": os.environ.get("LUMEN_QUICK_CHANGE_PROJECT", ""),
        "user_message": os.environ.get("LUMEN_QUICK_CHANGE_USER_MESSAGE", request),
    }
    lock = _lock_path(workspace_root)
    worktree: Path | None = None
    lock_owned = False
    success = False
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock.mkdir(exist_ok=False)
        except FileExistsError as exc:
            raise QuickChangeBlocked("another delivery or quick change is already active") from exc
        lock_owned = True
        (lock / "pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
        (lock / "started_at").write_text(f"{utc_now()}\n", encoding="utf-8")
        write_json(result_path, result)

        base = resolve_repo_default_branch(repository, source_repo, workspace_root)
        remote = run_git(source_repo, "remote", "get-url", "origin")
        if remote.returncode == 0:
            fetched = run_git(source_repo, "fetch", "origin", base)
            if fetched.returncode != 0:
                raise RuntimeError(_git_text(fetched, f"failed to fetch origin/{base}"))
            base_ref = f"origin/{base}"
        else:
            base_ref = base
        base_head = run_git(source_repo, "rev-parse", f"{base_ref}^{{commit}}")
        if base_head.returncode != 0:
            raise RuntimeError(_git_text(base_head, f"base branch not found: {base_ref}"))

        branch = f"chore/lumen-quick-{slugify(repository) or 'change'}-{run_id[-8:]}"
        worktree = delivery_worktrees_dir(workspace_root) / "quick" / run_id / repository
        worktree.parent.mkdir(parents=True, exist_ok=True)
        created = run_git(source_repo, "worktree", "add", "-B", branch, str(worktree), base_ref)
        if created.returncode != 0:
            raise RuntimeError(_git_text(created, "unable to create isolated quick-change worktree"))
        _set_result(result_path, result, branch=branch, worktree=str(worktree), base_branch=base)

        execution = delivery_config.get("execution") if isinstance(delivery_config.get("execution"), dict) else {}
        model = str(os.environ.get("CURSOR_AGENT_MODEL") or execution.get("model") or "cursor-grok-4.5-medium").strip()
        prompt = (
            "You are Lumen's bounded Quick Change Worker.\n"
            "Work only in this isolated worktree. Do not modify the docs workspace, Story files, Jira, or secrets.\n"
            "Do not commit, push, create a PR, or change files outside the approved target list.\n\n"
            f"Repository: {repository}\n"
            f"Request: {request}\n"
            f"Approved target files: {', '.join(target_files)}\n"
            f"Target version: {target_version or '(not a version bump)'}\n\n"
            "Inspect the existing files first and make the smallest correct change. For a version bump, update the "
            "canonical version value in the approved file(s); do not touch lockfiles or unrelated generated files "
            "unless they are explicitly approved above. If the request cannot be performed safely within this "
            "scope, make no changes and exit with an explanation."
        )
        _run_agent(worktree, prompt, log_path, model, repository)
        current_head = run_git(worktree, "rev-parse", "HEAD")
        if current_head.returncode != 0 or current_head.stdout.strip() != base_head.stdout.strip():
            raise QuickChangeBlocked("Agent created a commit; quick changes require host-side commit control")
        changed = _change_scope(worktree, target_files, target_version, is_version_change(request, change_type))
        _set_result(result_path, result, status="verifying", delivery_status="verifying", files_changed=changed)
        verification_results = _verify(
            workspace_root=workspace_root,
            worktree=worktree,
            repository=repository,
            delivery_config=delivery_config,
        )
        _set_result(result_path, result, verification_results=verification_results)
        failed = [item for item in verification_results if item.get("status") == "failed"]
        if failed:
            raise RuntimeError("quick-change verification failed")
        if args.dry_run:
            _set_result(result_path, result, status="dry_run", delivery_status="completed", publish_mode="none", finished_at=utc_now())
            success = True
            return 0

        mode = configured_publish_mode(delivery_config)
        subject = lumen_commit_subject("N/A", request.replace(chr(10), " ")[:100], kind="chore")
        commit_sha = commit_changes(worktree, subject, repository)
        publish_item: dict[str, Any] = {"mode": mode}
        pr_urls: list[str] = []
        if mode == "direct":
            push_default_branch(worktree, base, repository)
            publish_item["status"] = "direct"
        elif mode in {"pr", "merge"}:
            title = subject[:120]
            body = (
                "## Lumen Quick Change\n\n"
                f"Repository: `{repository}`\n\n"
                f"Request: {request}\n\n"
                f"Target files: {', '.join(f'`{item}`' for item in target_files)}\n\n"
                "Verification was run by the Lumen quick-change worker."
            )
            url = open_pr_with_retry(worktree, branch, base, title, body, repository)
            pr_urls.append(url)
            publish_item.update({"status": "pr_open" if mode == "pr" else "merged", "pr_url": url})
            if mode == "merge":
                merge_pr(worktree, url, repository)
        else:
            publish_item["status"] = "local_only"
        _set_result(
            result_path,
            result,
            status="completed",
            delivery_status="completed",
            finished_at=utc_now(),
            commits=[{"repository": repository, "sha": commit_sha, "subject": subject}],
            pr_urls=pr_urls,
            publish_mode=mode,
            publish=publish_item,
        )
        try:
            from deployment_tracking import launch_tracker

            launch_tracker(result_path, "quick_change")
        except Exception as exc:
            _set_result(result_path, result, deployment_tracking_error=str(exc)[:500])
        success = True
        return 0
    except Exception as exc:
        if result_path.parent:
            status = "blocked" if isinstance(exc, (QuickChangeBlocked, ValueError)) else "failed"
            _set_result(result_path, result, status=status, delivery_status=status, error=str(exc)[:1000], finished_at=utc_now())
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if lock_owned and lock.is_dir():
            for name in ("pid", "started_at"):
                (lock / name).unlink(missing_ok=True)
            lock.rmdir()
        automation_config = delivery_config.get("automation") if isinstance(delivery_config.get("automation"), dict) else {}
        if success and worktree is not None and bool(automation_config.get("cleanup_worktrees_on_success", True)):
            _remove_worktree(source_repo, worktree)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_dir")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--change-type", default="small_change")
    parser.add_argument("--target-version", default="")
    parser.add_argument("--target-file", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    try:
        return run(parser.parse_args(argv))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
