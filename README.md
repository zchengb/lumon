# Lumon v1

Lumon v1 is the greenfield Python CLI for creating and inspecting a local
Workspace. The v1 runtime is intentionally limited to the CLI, Workspace
skeleton, and bundled global planning Skills installation.

## Install on a new machine

Lumon uses an isolated Python 3.12 environment managed by `uv`:

```text
uv python install 3.12
uv tool install --python 3.12 /path/to/lumon-0.1.0-py3-none-any.whl
lumon doctor
```

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

The v1 source tree intentionally contains only `src/lumon` and `tests/v1`.
