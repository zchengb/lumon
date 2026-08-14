#!/usr/bin/env python3
"""Create delivery commits and publish them by PR, merge, or direct push."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from delivery_result_merge import stabilize_delivery_result
from delivery_workspace import delivery_config_path, load_story_context, read_json, write_json
from git_publish import (
    PUBLISH_RETRY_ATTEMPTS,
    PUBLISH_RETRY_DELAYS_SECONDS,
    branch_has_commits,
    changed_files,
    commit_changes,
    ensure_branch,
    merge_pr,
    open_pr,
    publish_retriable,
    push_default_branch,
    run_git,
)
from sync_delivery_docs import normalize_lumon_commit_subject


def open_pr_with_retry(repo: Path, branch: str, base: str, title: str, body: str, repo_name: str) -> str:
    last_error = ""
    for attempt in range(1, PUBLISH_RETRY_ATTEMPTS + 1):
        try:
            return open_pr(repo, branch, base, title, body, repo_name)
        except RuntimeError as exc:
            last_error = str(exc)
            if attempt >= PUBLISH_RETRY_ATTEMPTS or not publish_retriable(last_error):
                break
            time.sleep(PUBLISH_RETRY_DELAYS_SECONDS[min(attempt - 1, len(PUBLISH_RETRY_DELAYS_SECONDS) - 1)])
    raise RuntimeError(f"{repo_name}: publish failed after {PUBLISH_RETRY_ATTEMPTS} attempt(s): {last_error}")


def commit_subject(result: dict[str, Any], repo_name: str, ticket: str = "N/A") -> str:
    for item in result.get("repos_touched") or []:
        if isinstance(item, dict) and str(item.get("name", "")) == repo_name:
            subject = str(item.get("commit_subject", "")).strip()
            if subject:
                return normalize_lumon_commit_subject(subject, ticket)
    raise RuntimeError(
        f"{repo_name}: Agent did not provide commit_subject in delivery-result.json. "
        "Remediation must preserve commit_subject entries for every repository with changes."
    )


def update_result(path: Path, payload: dict[str, Any]) -> None:
    payload["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_json(path, payload)


def visual_pr_summary(result: dict[str, Any]) -> str:
    visual = result.get("visual_verification")
    if not isinstance(visual, dict):
        return ""
    lines = ["\n\n## Visual Verification\n", "| Screen | State | Platform | Result | Difference |", "|---|---|---|---|---|"]
    for item in visual.get("results", []):
        if not isinstance(item, dict):
            continue
        ratio = item.get("difference_ratio")
        difference = f"{float(ratio):.2%}" if isinstance(ratio, (int, float)) else "N/A"
        lines.append(
            f"| {item.get('screen', '')} | {item.get('state', '')} | {item.get('platform', '')} | "
            f"{str(item.get('status', '')).title()} | {difference} |"
        )
    lines.append("\nReference, implementation, and diff images are retained in Lumen delivery history.")
    return "\n".join(lines)


def record_failure(result: dict[str, Any], detail: str) -> None:
    failures = result.get("failures") if isinstance(result.get("failures"), list) else []
    failures.append({"stage": "finalize", "detail": detail})
    result["failures"] = failures
    result["delivery_status"] = "blocked"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_dir")
    parser.add_argument("--story", default="")
    parser.add_argument("--result", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result_path = Path(args.result).expanduser().resolve()
    result = read_json(result_path)
    if not result:
        print(f"Error: delivery result not found or invalid: {result_path}", file=sys.stderr)
        return 1

    try:
        context = load_story_context(Path(args.docs_dir), args.story, validate_gates=False)
        config = read_json(delivery_config_path(context.workspace_root), {})
        publish = config.get("publish") if isinstance(config.get("publish"), dict) else {}
        publish_mode = str(publish.get("mode", "pr")).strip().lower() or "pr"
        if publish_mode not in {"none", "pr", "merge", "direct"}:
            raise RuntimeError("Delivery publish mode must be 'none', 'pr', 'merge', or 'direct'")
        if str(result.get("delivery_status", "")).strip() not in {"completed", "ready_for_finalize"}:
            raise RuntimeError("Agent result must be completed or ready_for_finalize before finalization")
        result = stabilize_delivery_result(result, context, result_path)
        commits: list[dict[str, str]] = []
        pr_urls: list[str] = []
        touched: list[dict[str, Any]] = []
        body = (
            f"Story: {context.metadata.get('title') or context.story_dir.name}\n\n"
            f"JIRA: {context.metadata.get('jiraUrl') or context.metadata.get('jiraKey') or 'Not linked'}\n\n"
            "Verification is recorded by Lumen in the delivery result."
        ) + visual_pr_summary(result)

        base_commit = str(context.metadata.get("baseCommit") or context.metadata.get("base_commit") or "").strip()
        for repo in context.repos:
            ensure_branch(repo.worktree_path, context.branch_name, repo.name)
            files = changed_files(repo.worktree_path)
            item: dict[str, Any] = {
                "name": repo.name,
                "path": str(repo.worktree_path),
                "branch": context.branch_name,
                "files_changed": files,
            }
            ticket = str(context.metadata.get("jiraKey") or context.story_dir.name or "N/A").strip()
            subject = commit_subject(result, repo.name, ticket) if files else ""
            if files:
                sha = commit_changes(repo.worktree_path, subject, repo.name)
                commits.append({"repository": repo.name, "sha": sha, "subject": subject})
                item["commit_subject"] = subject
            else:
                head = run_git(repo.worktree_path, "rev-parse", "HEAD")
                if head.returncode == 0:
                    item["existing_head"] = head.stdout.strip()

            if not branch_has_commits(repo.worktree_path, repo.default_branch, repo.name, base_commit):
                item["publish_status"] = "skipped"
                item["publish_reason"] = "No commits differ from the base branch"
                touched.append(item)
                continue

            if args.dry_run:
                item["pr_url"] = "(dry-run)"
                item["publish_status"] = "dry_run"
            elif publish_mode == "none":
                item["publish_status"] = "skipped"
                item["publish_reason"] = "Publishing disabled for verification run"
            else:
                if publish_mode == "direct":
                    push_default_branch(repo.worktree_path, repo.default_branch, repo.name)
                    item["publish_status"] = "direct"
                else:
                    pr_title = subject or f"{context.metadata.get('jiraKey') or context.story_dir.name}: delivery"
                    url = open_pr_with_retry(
                        repo.worktree_path,
                        context.branch_name,
                        repo.default_branch,
                        pr_title,
                        body,
                        repo.name,
                    )
                    item["pr_url"] = url
                    item["publish_status"] = "pr_open"
                    pr_urls.append(url)
                    if publish_mode == "merge":
                        merge_pr(repo.worktree_path, url, repo.name)
                        item["merged"] = True
                        item["publish_status"] = "merged"
            touched.append(item)

        result["repos_touched"] = touched
        result["commits"] = commits
        result["pr_urls"] = pr_urls
        result["publish_mode"] = publish_mode
        result["delivery_status"] = "completed"
        update_result(result_path, result)
        print(json.dumps({"commits": commits, "pr_urls": pr_urls}, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        record_failure(result, detail)
        update_result(result_path, result)
        print(f"Error: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
