#!/usr/bin/env python3
"""Commit and publish an Auto Patch result after the Agent exits."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from git_publish import (
    branch_has_commits,
    changed_files,
    commit_changes,
    ensure_branch,
    open_pr_with_retry,
    push_default_branch,
    run_git,
)
from patch_runtime import load_delivery_config, publish_mode, read_json, result_path, write_json
from delivery_workspace import workspace_lumen_dir
from sync_delivery_docs import normalize_lumon_commit_subject


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_subject(subject: str, key: str) -> str:
    return normalize_lumon_commit_subject(
        subject,
        key,
        default_kind="fix",
        default_summary="apply Auto Patch correction",
    )


def subject_for(agent_result: dict[str, Any], repository: str, key: str) -> str:
    for item in agent_result.get("repos_touched") or []:
        if isinstance(item, dict) and str(item.get("name") or "").strip() == repository:
            subject = str(item.get("commit_subject") or "").strip()
            if subject:
                return normalize_subject(subject, key)
    return normalize_subject("", key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--result")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    result_file = Path(args.result).expanduser().resolve() if args.result else result_path(workspace)
    result = read_json(result_file, {})
    progress = read_json(workspace_lumen_dir(workspace) / "results" / "patch-progress.json", {})
    if not result:
        print(f"Error: Auto Patch result not found: {result_file}", file=__import__("sys").stderr)
        return 1
    try:
        if str(result.get("patch_status") or "").strip() != "completed":
            raise RuntimeError("Agent result must be completed before finalization")
        key = str(result.get("jira_key") or progress.get("jira_key") or "").strip().upper()
        mode = publish_mode(workspace)
        commits: list[dict[str, str]] = []
        pr_urls: list[str] = []
        touched: list[dict[str, Any]] = []
        changed = False
        for repo in progress.get("repositories") or []:
            if not isinstance(repo, dict):
                continue
            name = str(repo.get("name") or "").strip()
            worktree = Path(str(repo.get("worktree_path") or "")).expanduser().resolve()
            if not name or not worktree.is_dir():
                continue
            base = str(repo.get("default_branch") or "main").strip()
            branch = str(repo.get("branch") or "").strip()
            ensure_branch(worktree, branch, name)
            files = changed_files(worktree)
            item: dict[str, Any] = {"name": name, "path": str(worktree), "branch": branch, "files_changed": files}
            if files:
                changed = True
                subject = subject_for(result, name, key)
                if not args.dry_run:
                    sha = commit_changes(worktree, subject, name)
                    commits.append({"repository": name, "sha": sha, "subject": subject})
                item["commit_subject"] = subject
            if not branch_has_commits(worktree, base, name):
                item["publish_status"] = "skipped"
                item["publish_reason"] = "No commits differ from the base branch"
                touched.append(item)
                continue
            if args.dry_run:
                item["publish_status"] = "dry_run"
            elif mode == "direct":
                push_default_branch(worktree, base, name)
                item["publish_status"] = "direct"
            else:
                title = str(result.get("summary") or f"{key}: Auto Patch").strip()
                body = f"Auto Patch for {key}.\n\n{result.get('summary', '')}\n\nVerification is recorded in the Lumen patch result."
                url = open_pr_with_retry(worktree, branch, base, title, body, name)
                item["pr_url"] = url
                item["publish_status"] = "pr_open"
                pr_urls.append(url)
            touched.append(item)
        if not touched or not changed:
            raise RuntimeError("Auto Patch produced no repository changes")
        result.update({"repos_touched": touched, "commits": commits, "pr_urls": pr_urls, "publish_mode": mode, "patch_status": "completed", "finished_at": utc_now()})
        write_json(result_file, result)
        print(json.dumps({"commits": commits, "pr_urls": pr_urls}, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        result.setdefault("failures", []).append({"stage": "finalize", "detail": str(exc)})
        result.update({"patch_status": "blocked", "finished_at": utc_now()})
        write_json(result_file, result)
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
