# Lumon v1

Lumon v1 is the greenfield Python CLI and local Dashboard for creating,
inspecting, and switching between local Workspaces. The v1 runtime contains
the CLI, Workspace skeleton, bundled global planning Skills installation, and
the Dashboard's Workspace overview and typed settings.

## Install from GitHub

Lumon is distributed only through this GitHub repository. Stable releases are
attached to GitHub Releases; the CI build is also retained as a GitHub Actions
Artifact. Lumon is not published to PyPI or another public package index.

For a one-command Shell installation, use the installer in
`packaging/install.sh`. It does not use uv; it creates an isolated Python 3.12
virtual environment and installs Lumon with pip. When no version is provided,
the installer resolves the latest stable GitHub Release and verifies the Wheel
with its `SHA256SUMS` file. A specific version can still be pinned explicitly.
Pass `--observability` when the Mark Agent should include the optional Langfuse
Cloud SDK in the installation.
On a private repository, provide `LUMON_GITHUB_TOKEN` or use an SSH-accessible
repository. The matching uninstaller is `packaging/uninstall.sh`.

For the public repository, install the latest stable Release with:

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash
```

To pin a version, append the installer argument after `bash -s --`:

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash -s -- --version v1.0.14
```

To install the optional Langfuse Cloud telemetry support, add the installer
flag:

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash -s -- --observability
```

The installer does not modify a Workspace or remove global Skills. To remove
the Shell installation later, run:

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/uninstall.sh | bash
```

After a newer GitHub Release is published, a Shell-installed CLI can update
itself with:

```text
lumon update
lumon update --check
```

For a private repository, provide `LUMON_GITHUB_TOKEN` in the process
environment when checking or applying an update. Tokens are never written to
the Workspace or command output. Existing installations made with uv retain
their uv-based update path.

Each push to `release` runs tests and uploads a temporary build artifact. A
semantic version tag such as `v1.0.14` runs the release workflow, which attaches
the Wheel, source distribution, and `SHA256SUMS` to a GitHub Release.

## Initialize a Workspace

```text
lumon init /path/to/lumon-workspace
```

With one or more code Repositories, repeat `--repository`:

```text
lumon init /path/to/lumon-workspace \
  --repository git@github.com:example/product.git \
  --repository git@github.com:example/backend.git
```

When `--repository` is omitted in an interactive terminal, Lumon asks for
clone URLs one at a time; an empty URL ends the collection. In a non-interactive
process, or with `--json`, omission means an intentionally empty Workspace.
Repository names are derived from the URLs, and credentials must come from the
system Git SSH agent or credential helper rather than the URL itself.

For each new Repository, Lumon probes `main` first and otherwise uses the
remote's advertised default branch. It records the actual branch, revision,
URL, and `repos/<name>` path in `lumon/workspace.toml`. A matching existing Git
checkout is reused without fetch, reset, checkout, or deletion. A different
remote or an existing non-Git directory is rejected. Initialization is
transactional: newly cloned repositories and newly installed Skills are
removed if the operation fails.

When Mark is already configured and the initialized Workspace is the only
registered Workspace, `lumon init` selects it as Mark's default automatically.
When multiple Workspaces are registered, initialization leaves the existing
default unchanged.

Initialization creates the Workspace skeleton, including a local `AGENTS.md`,
and installs the bundled `lumon-story-planning` and
`lumon-technical-planning` Skills when they do not already exist in
`~/.agents/skills/`. Existing Skill directories are left unchanged. Re-running
the command is safe and does not initialize Git or create a commit. Skills are
global Agent instructions; `AGENTS.md` contains rules specific to this
Workspace.

Useful commands:

```text
lumon --help
lumon help
lumon --version
lumon doctor [--workspace /path/to/lumon-workspace]
lumon init /path/to/lumon-workspace --dry-run
lumon init /path/to/lumon-workspace --json
lumon workspace list
lumon workspace set-default <workspace-id-or-path>
lumon workspace remove <workspace-id-or-path>
lumon ui --no-open
```

Workspace registrations are managed outside the Workspace directory. Use
`lumon workspace list` to find a Workspace ID, then
`lumon workspace set-default <workspace-id-or-path>` when Mark has more than
one registered Workspace. Use `lumon workspace set-default --clear` to remove
the default selection without removing a Workspace. `lumon workspace remove
<workspace-id-or-path>` clears Mark's default when the target is selected, then
removes the registry entry and its user-level profile while keeping the
Workspace files; add `--delete` to permanently delete the Workspace directory
and its cloned Repositories, and use `--yes` to skip the confirmation prompt.

## Dashboard

Start the local Dashboard with:

```text
lumon ui
```

Lumon binds the Python API to `127.0.0.1`, selects an available port, and opens
the browser. Use `lumon ui --no-open` when the browser should not be opened.
The Dashboard can initialize a new Workspace, add an existing initialized
Workspace, switch between registered Workspaces, inspect Repository health,
and configure the current Workspace's Feishu Webhook.

The machine-local registry and Workspace profiles live under `~/.lumon/`:

```text
~/.lumon/
├── registry.toml
└── workspaces/<workspace-id>/config.toml
```

The profile is per user and per Workspace. Webhook URLs are not written to
the Workspace repository, returned by the Dashboard API, or included in
Lumon logs. Existing Workspace directories are not discovered by scanning;
add them explicitly from the onboarding page or with `lumon ui --workspace`.

The v1 source tree intentionally contains only the new `src/lumon` modules,
the Dashboard frontend source, and the unified `tests` directory. The old
main branch Dashboard and runtime are not imported or packaged.

## Mark Agent

Mark is the local Workspace Agent. It listens for Feishu messages over the
official WebSocket Channel SDK, handles private messages and group messages
that explicitly mention `@Mark`, and runs the user's request through the
configured local Agent CLI in the Workspace. Codex is the only supported
provider today; Mark depends on a provider-neutral runner contract so another
CLI can be added without changing message handling, Workspace context, or
persistence. It sends short progress messages and a final answer back to the
same chat thread.

Configure and inspect it with:

```text
lumon agent configure
lumon agent doctor
lumon agent start
```

Use `lumon agent start --background`, `lumon agent status`, and
`lumon agent stop` for a detached local process. Mark is deliberately not
started by `lumon ui`.

Mark configuration is kept separately from Workspace settings in
`~/.lumon/agent.toml` (or `$LUMON_HOME/agent.toml`) and its SQLite state is in
`~/.lumon/mark.sqlite3`. The App Secret is stored in the owner-only `600`
configuration file and never appears in CLI output, logs, or Feishu replies.
Mark uses Codex CLI model `gpt-5.6-luna` with `max` reasoning effort by default.
The `agent_model` and `agent_reasoning_effort` fields in `agent.toml` can be
edited to choose another supported model and effort; `lumon agent doctor`
shows the selected pair. Existing `codex_model` files are read for compatibility
and normalized when they are next saved.
Mark's packaged templates are kept together under
`lumon/agents/mark/templates/`, including `SOUL.md` and the Workspace Prompt
template. A user-owned SOUL override can be placed at
`~/.lumon/agents/mark/templates/SOUL.md` and is never overwritten
automatically. See [docs/mark-agent.md](docs/mark-agent.md) for the Feishu
application setup, Langfuse Cloud pilot configuration, and the full local
verification flow.

Codex execution is a reusable tool under `lumon/tools/codex.py`, not a Mark-only
implementation. Mark adds its conversational progress and final-text policy in
its own runner; future flows such as Auto Scan can call the same tool and use
only the execution status or file events.

Mark keeps conversation state in explicit SQLite tables. A direct Feishu chat
uses one durable Session regardless of reply-thread metadata; a group Feishu
Thread uses its own Session. The Session stores the native Codex thread ID, so
a restart does not break the conversation. The first turn sends and stores the
complete bootstrap Prompt in `runs.prompt_text`; later turns call
`codex exec resume <session-id>` and send only the new user message. The later
`prompt_text` value is therefore the actual incremental input, while the first
Run retains the full Mark, Workspace, history, and user context used to
establish the native Codex Session. If the native Session is lost or the
Workspace changes, Lumon clears the binding and starts a new bootstrap on the
next message instead of automatically retrying the failed request. Prompts are
never written to logs, CLI output, or Feishu replies, but they may contain
Workspace-sensitive context; protect the owner-only `600` SQLite file
accordingly.
