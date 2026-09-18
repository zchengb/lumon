# Lumon Workspace

This directory is a Lumon Workspace initialized by Lumon.

## Local rules

- Keep Workspace capabilities under `lumon/capabilities/`; each capability is a Markdown file with TOML frontmatter.
- Treat `lumon/manifest.json` as the identity and initialization record for this Workspace.
- Keep cloned code Repositories under `repos/`; Lumon does not modify their working trees during initialization.
- Keep runtime outputs under `lumon/runs`, `lumon/artifacts`, `lumon/logs`, and `lumon/tmp`.
- Keep user-defined Agent flows under `lumon/flows/`; each flow is a Markdown file with TOML frontmatter.
- Do not store secrets in this Workspace.
- Global Agent Skills live under `~/.agents/skills/`; do not copy them into this Workspace.
- Use `lumon doctor --workspace <path>` for read-only Workspace checks.
- Add Workspace-specific rules here instead of changing the global Skills.

## Repository freshness

At the start of every task, read the current `AGENTS.md`, `lumon/manifest.json`, and `lumon/workspace.toml`, then inspect every Repository registered in `workspace.toml`. Use each Repository's relative `path` as the active checkout; `url` is only the initialization source and must not be used as the daily sync target.

- Check each Repository's worktree, configured branch, upstream, and working-tree status.
- Pull only clean Repositories on their configured branch when `git pull --ff-only` is safe.
- If a Repository has local changes, skip the pull and report it. Never stash, reset, overwrite, or discard user work.
- If a Repository is diverged, has no usable upstream, has a branch mismatch, or cannot reach its remote, stop work that depends on it and explain the blocker.
- Report only sanitized Repository names, branches, statuses, and failure reasons. Never expose remote URLs containing credentials, secrets, or raw sensitive command output.

## Code change isolation

Registered code Repositories are read-only in their canonical `repos/` checkouts. Make code changes, run checks, and create commits only in an independent worktree:

`<workspace>/lumon/worktrees/<task-key>/<repository>/`

- Create a branch named `lumon/<task-key>/<repository>` from that Repository's configured base branch; do not assume the base branch is `main`.
- Reuse an existing worktree only when its path, branch, base, and status are consistent. Never reset or overwrite it.
- Workspace-owned files such as `AGENTS.md`, Flows, and Capabilities may be edited directly in the Workspace.
- After the task is complete and the worktree is clean, remove the worktree automatically. Keep its branch, commits, and any PR.
- Never remove a worktree with uncommitted or untracked changes, incomplete validation, or pending publication; report it and ask how to proceed.
- Keep a worktree only when the user explicitly asks for it to remain available.

## Validation

Before editing a code Repository, inspect its local instructions, README, CI configuration, project manifests, lock files, and available scripts to determine the appropriate checks.

- Prefer the Repository's existing virtual environment, toolchain, lockfile, and documented bootstrap commands.
- Do not install global dependencies, change lock files, or disguise environment failures as code success.
- Run the strongest feasible level: full project checks first, then targeted checks, then syntax/import/compile checks for historical or otherwise un-runnable projects.
- Record the environment, exact commands, results, skipped checks, and reasons. “Not run” and “syntax-only” are not “tests passed”.
- If publication was requested but only fallback validation is possible, explain the evidence and remaining risk and get user confirmation before committing or pushing.

## Commit and publication

- Do not upgrade versions, commit, push, or create a PR unless the user explicitly requests publication.
- An explicit `commit`/`push` request establishes publication intent, but does not guess an unspecified destination. If the destination is not stated, ask whether to open a PR, update the configured base branch directly, or keep the commit local.
- PR mode pushes the isolated feature branch and opens a PR.
- Direct-base mode updates the configured base branch only through a verified fast-forward; never force-push.
- Keep the canonical checkout untouched and do not remove the worktree automatically.
