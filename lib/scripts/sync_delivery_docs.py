#!/usr/bin/env python3
"""Commit and push Lumen-owned docs changes without touching unrelated user edits."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from delivery_workspace import load_story_context, workspace_lumen_dir
from git_sync import clear_conflict, run_git, save_conflict

METADATA_PATH = re.compile(r"^stories/[^/]+/metadata\.json$")
CONFIG_PATH = re.compile(r"^lumen/config/.+\.json$")
_COMMIT_KINDS = "chore|docs|feat|fix|refactor|style|test"
_CANONICAL_SUBJECT = re.compile(
    rf"^\[[^\]\r\n]+\]\s+#\S+\s+(?P<kind>{_COMMIT_KINDS}):\s*(?P<summary>.+)$",
    re.IGNORECASE,
)
_CONVENTIONAL_SUBJECT = re.compile(
    rf"^(?P<kind>{_COMMIT_KINDS})(?:\([^\r\n)]*\))?\s*:\s*(?P<summary>.+)$",
    re.IGNORECASE,
)


def failure_text(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    return (result.stderr or result.stdout or fallback).strip()


def lumen_commit_subject(ticket: str, summary: str, *, kind: str = "feat") -> str:
    key = str(ticket or "").strip().lstrip("#") or "N/A"
    change = str(kind or "feat").strip().lower() or "feat"
    text = " ".join(str(summary or "").strip().split())
    if not text:
        text = "update delivery docs"
    return f"[lumon] #{key} {change}: {text}"


def normalize_lumon_commit_subject(
    subject: str,
    ticket: str,
    *,
    default_kind: str = "feat",
    default_summary: str = "update delivery docs",
) -> str:
    """Convert agent/history subjects to the canonical Lumon commit format."""
    raw = " ".join(str(subject or "").strip().split())
    kind = str(default_kind or "feat").strip().lower() or "feat"
    summary = raw or default_summary
    match = _CANONICAL_SUBJECT.match(raw) or _CONVENTIONAL_SUBJECT.match(raw)
    if match:
        kind = match.group("kind").lower()
        summary = match.group("summary").strip()
    return lumen_commit_subject(ticket, summary, kind=kind)


def porcelain_paths(docs_dir: Path) -> list[str]:
    status = run_git(docs_dir, "status", "--porcelain")
    if status.returncode != 0:
        raise RuntimeError(f"Docs directory is not a git repository: {docs_dir}")
    paths: list[str] = []
    for line in status.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if path:
            paths.append(path)
    return paths


def classify_dirty_paths(docs_dir: Path) -> tuple[list[str], list[str], list[str]]:
    metadata: list[str] = []
    config: list[str] = []
    foreign: list[str] = []
    for path in porcelain_paths(docs_dir):
        if METADATA_PATH.match(path):
            metadata.append(path)
        elif CONFIG_PATH.match(path):
            config.append(path)
        else:
            foreign.append(path)
    return metadata, config, foreign


def ticket_from_metadata_file(docs_dir: Path, relative_path: str) -> str:
    try:
        payload = json.loads((docs_dir / relative_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("jiraKey") or payload.get("storyId") or "").strip()


def current_branch(docs_dir: Path) -> str:
    branch = run_git(docs_dir, "branch", "--show-current")
    name = branch.stdout.strip()
    if branch.returncode != 0 or not name:
        raise RuntimeError(failure_text(branch, "Docs repository is not on a branch"))
    return name


def integrate_remote_and_push(docs_dir: Path, branch_name: str, subject: str = "") -> str:
    """Rebase onto remote updates when needed, then push. Raises on conflict."""
    fetch = run_git(docs_dir, "fetch", "origin", branch_name)
    if fetch.returncode != 0:
        # First push / missing remote branch — try push anyway.
        detail = failure_text(fetch, "fetch failed")
        pushed = run_git(docs_dir, "push", "-u", "origin", f"HEAD:{branch_name}")
        if pushed.returncode != 0:
            raise RuntimeError(failure_text(pushed, f"git push failed after fetch error: {detail}"))
        clear_conflict(workspace_lumen_dir(docs_dir) / "state")
        return "pushed"

    remote_ref = f"origin/{branch_name}"
    if run_git(docs_dir, "rev-parse", "--verify", remote_ref).returncode != 0:
        pushed = run_git(docs_dir, "push", "-u", "origin", f"HEAD:{branch_name}")
        if pushed.returncode != 0:
            raise RuntimeError(failure_text(pushed, "git push failed"))
        clear_conflict(workspace_lumen_dir(docs_dir) / "state")
        return "pushed"

    counts = run_git(docs_dir, "rev-list", "--left-right", "--count", f"HEAD...{remote_ref}")
    if counts.returncode != 0:
        raise RuntimeError(failure_text(counts, "Unable to compare local and remote docs branches"))
    parts = counts.stdout.strip().split()
    ahead = int(parts[0]) if parts else 0
    behind = int(parts[1]) if len(parts) > 1 else 0
    if behind > 0 and ahead == 0:
        pulled = run_git(docs_dir, "pull", "--ff-only", "origin", branch_name)
        if pulled.returncode != 0:
            save_conflict(
                workspace_lumen_dir(docs_dir) / "state",
                repo=docs_dir,
                branch=branch_name,
                remote_oid=run_git(docs_dir, "rev-parse", remote_ref).stdout.strip(),
                local_oid=run_git(docs_dir, "rev-parse", "HEAD").stdout.strip(),
                reason="Remote docs updates could not be fast-forwarded safely.",
                subject=subject,
            )
            raise RuntimeError(failure_text(pulled, "git pull --ff-only failed"))
        clear_conflict(workspace_lumen_dir(docs_dir) / "state")
        return "pulled"
    if behind > 0:
        rebase = run_git(docs_dir, "rebase", remote_ref)
        if rebase.returncode != 0:
            run_git(docs_dir, "rebase", "--abort")
            save_conflict(
                workspace_lumen_dir(docs_dir) / "state",
                repo=docs_dir,
                branch=branch_name,
                remote_oid=run_git(docs_dir, "rev-parse", remote_ref).stdout.strip(),
                local_oid=run_git(docs_dir, "rev-parse", "HEAD").stdout.strip(),
                reason="Remote docs updates conflict with local Lumen changes.",
                subject=subject,
            )
            raise RuntimeError(
                "Remote docs branch has updates that conflict with local Lumen commits; "
                "resolve it from the Dashboard before retrying"
            )
    if ahead == 0 and behind == 0:
        clear_conflict(workspace_lumen_dir(docs_dir) / "state")
        return "up to date"
    pushed = run_git(docs_dir, "push", "origin", f"HEAD:{branch_name}")
    if pushed.returncode != 0:
        if "non-fast-forward" in failure_text(pushed, "").lower() or "rejected" in failure_text(pushed, "").lower():
            save_conflict(
                workspace_lumen_dir(docs_dir) / "state",
                repo=docs_dir,
                branch=branch_name,
                remote_oid=run_git(docs_dir, "rev-parse", remote_ref).stdout.strip(),
                local_oid=run_git(docs_dir, "rev-parse", "HEAD").stdout.strip(),
                reason="Remote docs updates arrived while Lumen was publishing.",
                subject=subject,
            )
        raise RuntimeError(failure_text(pushed, "git push failed"))
    clear_conflict(workspace_lumen_dir(docs_dir) / "state")
    return "rebased and pushed" if behind > 0 else "pushed"


def commit_paths(docs_dir: Path, paths: list[str], subject: str, *, push: bool = True) -> str:
    if not paths:
        return "skipped"
    if not (docs_dir / ".git").exists():
        raise RuntimeError(f"Docs directory is not a Git repository: {docs_dir}")
    added = run_git(docs_dir, "add", "--", *paths)
    if added.returncode != 0:
        raise RuntimeError(failure_text(added, "git add failed"))
    committed = run_git(docs_dir, "commit", "--only", "-m", subject, "--", *paths)
    if committed.returncode != 0:
        raise RuntimeError(failure_text(committed, "git commit failed"))
    sha = run_git(docs_dir, "rev-parse", "HEAD").stdout.strip()
    if not push:
        return f"committed: {sha} {subject}"
    branch_name = current_branch(docs_dir)
    sync = integrate_remote_and_push(docs_dir, branch_name, subject)
    return f"committed: {sha} {subject} ({sync})"


def commit_story_metadata(docs_dir: Path, story_ref: str = "", *, push: bool = True, include_config: bool = False) -> str:
    context = load_story_context(docs_dir, story_ref, validate_gates=False)
    relative_metadata = str(context.metadata_path.relative_to(context.docs_dir))
    changed = run_git(context.docs_dir, "diff", "--quiet", "--", relative_metadata)
    staged = run_git(context.docs_dir, "diff", "--cached", "--quiet", "--", relative_metadata)
    _, config_paths, _ = classify_dirty_paths(context.docs_dir) if include_config else ([], [], [])
    metadata_changed = changed.returncode != 0 or staged.returncode != 0
    if not metadata_changed and not config_paths:
        return "skipped: metadata.json has no delivery changes"
    if changed.returncode not in {0, 1} or staged.returncode not in {0, 1}:
        raise RuntimeError("Unable to inspect docs metadata change")
    story_key = str(context.metadata.get("jiraKey") or context.metadata.get("storyId") or context.story_dir.name)
    subject = lumen_commit_subject(story_key, f"update {story_key} delivery status")
    paths = ([relative_metadata] if metadata_changed else []) + config_paths
    return commit_paths(context.docs_dir, paths, subject, push=push)


def commit_dirty_config(docs_dir: Path, summary: str = "update delivery config", *, push: bool = True) -> str:
    _, config, _ = classify_dirty_paths(docs_dir)
    if not config:
        return "skipped"
    return commit_paths(docs_dir, config, lumen_commit_subject("N/A", summary), push=push)


def heal_lumen_owned_docs_dirt(docs_dir: Path, *, push: bool = True) -> list[str]:
    """Commit Lumen-owned dirt so delivery can proceed. Raises if unrelated files are dirty."""
    metadata, config, foreign = classify_dirty_paths(docs_dir)
    if foreign:
        preview = ", ".join(foreign[:5])
        raise RuntimeError(
            f"Docs workspace has uncommitted changes; scheduled delivery will not pull or run ({preview})"
        )
    messages: list[str] = []
    for path in metadata:
        ticket = ticket_from_metadata_file(docs_dir, path) or path.split("/")[1]
        subject = lumen_commit_subject(ticket, f"update {ticket} delivery status")
        messages.append(commit_paths(docs_dir, [path], subject, push=push))
    if config:
        messages.append(commit_dirty_config(docs_dir, push=push))
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_dir")
    parser.add_argument("--story", default="")
    parser.add_argument("--heal", action="store_true", help="Commit all Lumen-owned dirty docs paths")
    parser.add_argument("--include-config", action="store_true", help="Include Lumen config changes with the Story metadata commit")
    args = parser.parse_args()

    try:
        docs_dir = Path(args.docs_dir).expanduser().resolve()
        if args.heal:
            messages = heal_lumen_owned_docs_dirt(docs_dir)
            if not messages:
                print("skipped: no Lumen-owned docs changes")
            else:
                for message in messages:
                    print(message)
            return 0
        print(commit_story_metadata(docs_dir, args.story, include_config=args.include_config))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
