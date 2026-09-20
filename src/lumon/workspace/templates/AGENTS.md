# Lumon Workspace

This directory is a Lumon Workspace initialized by Lumon. This file defines the default operating rules for every task in this Workspace.

## Workspace layout

- Keep Workspace capabilities under `lumon/capabilities/` and flows under `lumon/flows/`; each is a Markdown file with TOML frontmatter.
- Treat `lumon/manifest.json` as the Workspace identity and initialization record, and keep registered code Repositories under `repos/`.
- Keep runtime outputs under `lumon/runs`, `lumon/artifacts`, `lumon/logs`, and `lumon/tmp`.
- Do not store secrets in the Workspace. Global Agent Skills live under `~/.agents/skills/`; do not copy them here.
- Use `lumon doctor --workspace <path>` for read-only Workspace checks. Add Workspace-specific rules here instead of changing global Skills.

## Start of every task

1. Read the current `AGENTS.md`, `lumon/manifest.json`, and `lumon/workspace.toml`.
2. Inspect every Repository registered in `workspace.toml`. Use its relative `path` as the active checkout; `url` is only the initialization source, never the daily sync target.
3. Check each Repository's worktree, configured branch, upstream, and working-tree status.
4. Pull only a clean Repository on its configured branch when `git pull --ff-only` is safe. Skip dirty Repositories and report them.
5. For remote conflicts, fetch when possible, inspect the commit graph, and attempt the safest non-destructive resolution: fast-forward clean branches when possible; for divergence, preserve both sides and reconcile in an isolated task worktree or branch, preferring rebase when the local commits can be replayed cleanly. Never stash, reset, overwrite, discard, amend, rebase shared history, or force-push.
6. Report only sanitized Repository names, branches, statuses, and failure reasons. Never expose credential-bearing remote URLs or raw sensitive command output.

## Change isolation

- Treat canonical `repos/` checkouts as read-only. Make code changes, run checks, and create commits in an independent worktree at `<workspace>/lumon/worktrees/<task-key>/<repository>/`.
- Create `lumon/<task-key>/<repository>` from the Repository's configured base branch; do not assume the base branch is `main`.
- Reuse an existing worktree only when its task path, branch, base, and status are consistent. If it is dirty or inconsistent, report the conflict, impact, and recommended ways to proceed before taking further action.
- Workspace-owned files such as `AGENTS.md`, Flows, and Capabilities may be edited directly in the Workspace.
- After the task reaches a terminal state, validation and publication decisions are recorded, and the worktree is clean, remove it automatically. Keep its branch, commits, or PR. Do not remove a worktree with uncommitted or untracked changes, incomplete validation, or pending publication unless the user resolves the condition or asks to keep it.

## Validation

Before editing a code Repository, inspect its local instructions, README, CI configuration, project manifests, lock files, and available scripts.

- Prefer the Repository's existing virtual environment, toolchain, lockfile, and documented bootstrap commands.
- Do not install global dependencies, change lock files, or disguise environment failures as code success.
- Run the strongest feasible checks: full project checks first, then relevant targeted checks, then syntax/import/compile checks for historical or otherwise un-runnable projects.
- Record the environment, exact commands, results, skipped checks, and reasons. “Not run” and “syntax-only” are not “tests passed”.
- If publication is requested but only fallback validation is possible, explain the evidence and remaining risk and get user confirmation before committing or pushing.

## Commit and publication

- Upgrade versions, commit, push, or open a PR only when explicitly requested. A commit request does not authorize push or PR; ask when the push or PR target is ambiguous. PRs use isolated branches, direct-base updates must fast-forward, and force-push is forbidden.
- Before committing, read the target Repository's `AGENTS.md`, commit configuration, and recent non-merge, non-release commit history. Match its subject format and resolve the issue key from the current request, branch, or task; use `N/A` only when history accepts it, never reuse old keys or mention AI. If the format has an author prefix, use `lumon` (for example, `[lumon]`); otherwise do not add one. Do not change Git author or committer configuration.
- If a commit skill is available, follow it for Repository resolution, staging, diff review, and message generation.
- Stage only current-task files, preserve unrelated changes, run `git diff --cached --check`, and exclude secrets, credentials, prompts, temporary/IDE files, and unrelated generated artifacts.

## Blockers and task continuation

- When a task is blocked by a missing dependency, failed or incomplete validation, Repository state, an ambiguous target, or another external condition, state the evidence and impact. Offer two or three concrete next steps and identify the recommended option.
- Do not silently weaken validation, install global dependencies, discard changes, commit, push, or remove a worktree while waiting for a decision. If the user does not respond, leave the worktree and changes untouched, report their path and state, and wait.
- A repeated user message is a new request event. Within the same direct chat or group Thread, treat it as a continuation: inspect the previous task state before starting over.
- If the previous task failed or is waiting for a decision, report the existing state and offer resume, retry, or discard options. Do not repeat side effects automatically.
- Keep the canonical checkout untouched after the task is isolated in a worktree.

## Command conventions

- Agent commands run through the user's configured shell, which may be zsh on macOS.
- Never use zsh special or read-only parameter names as shell variables, especially `status`; use names such as `repo_state`, `worktree_state`, or `branch_state` instead.
- Keep repository inspection commands POSIX-compatible where practical. If a script requires Bash, invoke `bash -lc` explicitly.
