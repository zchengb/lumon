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

## Shell command compatibility

Agent commands run through the user's configured shell, which may be zsh on macOS.

- Never use zsh special or read-only parameter names as shell variables, especially `status`; use names such as `repo_state`, `worktree_state`, or `branch_state` instead.
- Keep repository inspection commands POSIX-compatible where practical. If a script requires Bash, invoke `bash -lc` explicitly.

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

## Blockers and user decisions

When a task cannot safely continue because of a missing dependency, failed or incomplete validation, Repository state, an ambiguous target, or another external condition:

- State the concrete blocker, the evidence, and its impact on the requested outcome.
- Offer two or three concrete next steps, identify the recommended option, and state the main trade-off of each option.
- Do not silently weaken validation, install global dependencies, discard changes, commit, push, or remove a worktree while waiting for the user's choice.
- If the user does not respond, leave the existing worktree and changes untouched, report its path and current state, and wait for a later instruction.

## Commit and publication

- Do not upgrade versions, commit, push, or create a PR unless the user explicitly requests publication.
- An explicit `commit`/`push` request establishes publication intent, but does not guess an unspecified destination. If the destination is not stated, ask whether to open a PR, update the configured base branch directly, or keep the commit local.
- Before creating a commit, read the target Repository's `AGENTS.md`, contribution and commit configuration, and recent non-merge, non-release commit history. Match the established subject language, type, scope, required prefix, issue-key placement, punctuation, and length; never copy an old issue key.
- If a commit skill is available in the Agent skill catalog, read and follow it for Repository resolution, staging, diff review, and commit-message generation. Do not assume a personal skill path exists on every machine; when it is unavailable, use the Repository's local rules and history.
- PR mode pushes the isolated feature branch and opens a PR.
- Direct-base mode updates the configured base branch only through a verified fast-forward; never force-push.

### Commit authorship and message checklist

When the user explicitly asks Lumon to create a commit in a registered Repository:

- Resolve the current issue or Jira key only from the current request, branch, or unambiguous task context. If none exists, use `N/A` only when that Repository's history accepts it; never invent or reuse an old key.
- Inspect the recent non-merge, non-release commit history and match its dominant format, including language, type, scope, prefix, issue-key placement, punctuation, and length. Do not mention AI in the subject.
- Set the Git author name to `Lumon` and use the Workspace or Repository-approved Lumon service email. Never use the operator's personal author identity; if no approved Lumon email is configured, stop and ask for it.
- Stage only files belonging to the current task. Preserve unrelated staged or unstaged changes; do not use `git add .` or `git add -A` by default.
- Review the staged diff and run `git diff --cached --check`. Do not commit secrets, credentials, prompts, temporary files, IDE files, or unrelated generated artifacts.
- Create one coherent commit only after the applicable validation is recorded. A commit request alone does not authorize a push or PR; follow the publication choice separately.
- Never amend, reset, rebase, force-push, or rewrite history. Verify the resulting author with `git log -1 --format='%an <%ae>'`.

## Task continuation and retry

- A repeated user message is a new request event. Within the same direct chat or the same group Thread, treat it as a continuation of the existing conversation and inspect the previous task state before starting over.
- If the previous task failed or is waiting for a decision, first report the existing state and offer resume, retry, or discard options. Do not repeat side effects automatically.
- Reuse an existing worktree only when its task path, branch, base, and status are consistent. If it is dirty or inconsistent, do not reset it or create another worktree over it; report the conflict and ask how to proceed.
- Keep the canonical checkout untouched. After the task reaches a terminal state, validation and any publication decision are recorded, and the worktree is clean, remove the worktree automatically unless the user asks to keep it.
