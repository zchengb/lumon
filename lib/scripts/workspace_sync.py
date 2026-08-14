#!/usr/bin/env python3
"""Synchronize the Lumen-owned delivery workspace with its Git remote."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from delivery_workspace import resolve_docs_dir, workspace_lumen_dir
from git_sync import run_git
from sync_delivery_docs import (
    current_branch,
    integrate_remote_and_push,
    lumen_commit_subject,
    porcelain_paths,
)


SAFE_ROOT_FILES = frozenset({".gitignore", "AGENTS.md", "README.md"})
SAFE_ROOT_DIRS = frozenset({"config", "lumon", "lumen", ".lumen", "stories", "standards", "templates", "topics"})
SENSITIVE_NAMES = frozenset({".env", ".env.local", ".env.common"})
SENSITIVE_SUFFIXES = (".key", ".pem", ".p12", ".pfx")


def is_lumen_owned_path(relative_path: str) -> bool:
    path = Path(str(relative_path or "").strip())
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return False
    if path.name in SENSITIVE_NAMES or path.name.endswith(SENSITIVE_SUFFIXES):
        return False
    if len(path.parts) == 1:
        return path.name in SAFE_ROOT_FILES
    return path.parts[0] in SAFE_ROOT_DIRS


def _commit_owned_changes(docs_dir: Path, paths: list[str]) -> tuple[str, list[str]]:
    owned = [path for path in paths if is_lumen_owned_path(path)]
    if not owned:
        return "", []
    added = run_git(docs_dir, "add", "--", *owned)
    if added.returncode != 0:
        raise RuntimeError((added.stderr or added.stdout or "git add failed").strip()[-500:])
    committed = run_git(
        docs_dir,
        "commit",
        "--only",
        "-m",
        lumen_commit_subject("N/A", "sync delivery workspace"),
        "--",
        *owned,
    )
    if committed.returncode != 0:
        raise RuntimeError((committed.stderr or committed.stdout or "git commit failed").strip()[-500:])
    return run_git(docs_dir, "rev-parse", "HEAD").stdout.strip(), owned


def _docs_dir(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if (candidate / "stories").is_dir() or (candidate / "AGENTS.md").is_file():
        return resolve_docs_dir(candidate)
    if candidate.name in {"lumon", "lumen", ".lumen"}:
        return resolve_docs_dir(candidate.parent)
    raise FileNotFoundError(f"Not a Lumen Workspace: {candidate}")


def sync(path: Path) -> dict[str, object]:
    docs_dir = _docs_dir(path)
    lumen_dir = workspace_lumen_dir(docs_dir)
    lock = lumen_dir / "locks" / "workspace-sync"
    delivery_lock = lumen_dir / "locks" / "delivery-run"
    if delivery_lock.is_dir():
        return {"status": "skipped", "reason": "delivery_running", "docs_dir": str(docs_dir)}
    try:
        lock.mkdir(parents=True)
    except FileExistsError:
        return {"status": "skipped", "reason": "sync_running", "docs_dir": str(docs_dir)}

    try:
        dirty = porcelain_paths(docs_dir)
        foreign = [path for path in dirty if not is_lumen_owned_path(path)]
        if foreign:
            fetched = run_git(docs_dir, "fetch", "--prune", "origin")
            return {
                "status": "blocked_dirty",
                "reason": "foreign_changes",
                "docs_dir": str(docs_dir),
                "dirty_paths": dirty[:40],
                "foreign_paths": foreign[:40],
                "fetch": "ok" if fetched.returncode == 0 else "failed",
            }

        branch = current_branch(docs_dir)
        commit, committed_paths = _commit_owned_changes(docs_dir, dirty)
        remote_sync = integrate_remote_and_push(
            docs_dir,
            branch,
            lumen_commit_subject("N/A", "sync delivery workspace"),
        )
        return {
            "status": "ok",
            "docs_dir": str(docs_dir),
            "branch": branch,
            "commit": commit,
            "committed_paths": committed_paths,
            "remote_sync": remote_sync,
        }
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()
    try:
        result = sync(Path(args.path))
    except Exception as exc:
        result = {"status": "error", "error": str(exc)[:500]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"ok", "skipped", "blocked_dirty"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
