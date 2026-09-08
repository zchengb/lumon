# Lumon v1

Lumon v1 is the greenfield Python CLI for creating and inspecting a local
Workspace. The v1 runtime is intentionally limited to the CLI, Workspace
skeleton, and bundled global planning Skills installation.

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
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/release/packaging/install.sh | bash -s -- --version v1.0.1
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
semantic version tag such as `v1.0.1` runs the release workflow, which attaches
the Wheel, source distribution, and `SHA256SUMS` to a GitHub Release.

## Initialize a Workspace

```text
lumon init /path/to/lumon-workspace
```

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
```

The v1 source tree intentionally contains only `src/lumon` and `tests`.
