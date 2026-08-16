#!/usr/bin/env python3
"""Compose the Auto Patch Agent prompt from modular snippets and runtime context."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from patch_runtime import patch_worktree_path, repo_registry, result_path, workspace_lumen_dir


SCRIPT_DIR = Path(__file__).resolve().parent
LUMEN_HOME = SCRIPT_DIR.parent


def prompts_dir(workspace: Path) -> Path:
    local = workspace_lumen_dir(workspace) / "prompts" / "patch"
    return local if (local / "manifest.json").is_file() else LUMEN_HOME / "templates" / "prompts" / "patch"


def compose(workspace: Path, key: str, summary: str, context_path: Path, repositories: list[dict]) -> str:
    root = prompts_dir(workspace)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    parts = []
    for name in manifest.get("inline", ["01-role-and-mission.md"]):
        content = (root / str(name)).read_text(encoding="utf-8")
        if str(name) == "09-output-contract.md":
            # Existing workspaces keep editable prompt copies; normalize the old
            # control-plane path without overwriting those user-owned files.
            content = content.replace("<workspace-root>/lumen/", "<workspace-root>/lumon/")
            content = content.replace("[lumen]", "[lumon]")
        parts.append(content.strip())
    rows = []
    for entry in manifest.get("catalog", []):
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("file") or "").strip()
        if not name:
            continue
        rows.append(f"- `{root / name}` — {entry.get('title', name)} ({entry.get('when', 'always')})")
    if rows:
        parts.append("# Patch Prompt Catalog\n\nRead every file marked `required` before handoff.\n\n" + "\n".join(rows))
    repo_lines = []
    for repo in repositories:
        name = str(repo.get("name") or "").strip()
        repo_lines.append(
            f"- `{name}`: source `{repo.get('path', '')}`, worktree `{patch_worktree_path(workspace, key, name)}`, default branch `{repo.get('default_branch', 'main')}`"
        )
    runtime = f"""# Patch Runtime Context

Workspace: {workspace}
Jira key: {key}
Jira summary: {summary}
Jira context snapshot: {context_path}
Patch result file: {result_path(workspace)}

## Registered repositories

{chr(10).join(repo_lines) or '- No registered repositories'}

## Repository mapping policy

The runtime has already resolved the target set from authoritative Jira labels/fields, explicit `Repository:` lines, related Jira context, matching Jira-key history, and focused local code evidence. Do not block merely because an unrelated repository name appears in a suggestion or example. Inspect the selected worktrees and `git log --all --grep=<current-or-related-Jira-key>` before asking a human. Multiple selected repositories are valid when they implement the same bounded flow.
"""
    parts.extend([runtime, "# Jira Context Snapshot\n\nRead the complete JSON snapshot at:\n\n" + str(context_path)])
    return "\n\n".join(parts).strip() + "\n"


def main() -> int:
    if len(sys.argv) != 5:
        print("Usage: compose_patch_prompt.py <workspace> <jira-key> <summary> <context-json>", file=sys.stderr)
        return 1
    workspace = Path(sys.argv[1]).expanduser().resolve()
    try:
        print(compose(workspace, sys.argv[2].strip().upper(), sys.argv[3], Path(sys.argv[4]).expanduser().resolve(), repo_registry(workspace)), end="")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
