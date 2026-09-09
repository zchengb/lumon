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
On a private repository, provide `LUMON_GITHUB_TOKEN` or use an SSH-accessible
repository. The matching uninstaller is `packaging/uninstall.sh`.

For the public repository, install the latest stable Release with:

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash
```

To pin a version, append the installer argument after `bash -s --`:

```text
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash -s -- --version v1.0.2
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
semantic version tag such as `v1.0.2` runs the release workflow, which attaches
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
lumon ui --no-open
```

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
