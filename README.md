# Lumon v1

Lumon v1 is the greenfield Python CLI for creating and inspecting a local
Workspace. The v1 runtime is intentionally limited to the CLI, Workspace
skeleton, and bundled global planning Skills installation.

## Install from GitHub

Lumon is distributed only through this GitHub repository. Stable releases are
attached to GitHub Releases; the CI build is also retained as a GitHub Actions
Artifact. Lumon is not published to PyPI or another public package index.

Install `uv` using the machine's approved package manager or the official
standalone binary, then use the release Wheel:

```text
uv python install 3.12
uv tool install --python 3.12 https://github.com/zchengb/lumon/releases/download/v1.0.0/lumon-1.0.0-py3-none-any.whl
lumon doctor
```

After a newer GitHub Release is published, update the installed CLI with:

```text
lumon update
lumon update --check
```

For a private repository, provide `LUMON_GITHUB_TOKEN` in the process
environment when checking or applying an update. Tokens are never written to
the Workspace or command output.

Each push to `release` runs tests and uploads a temporary build artifact. A
semantic version tag such as `v1.0.0` runs the release workflow, which attaches
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
lumon --version
lumon doctor [--workspace /path/to/lumon-workspace]
lumon init /path/to/lumon-workspace --dry-run
```

The v1 source tree intentionally contains only `src/lumon` and `tests`.
