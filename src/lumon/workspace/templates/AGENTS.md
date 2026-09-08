# Lumon Workspace

This directory is a Lumon Workspace initialized by Lumon.

## Local rules

- Treat `lumon/manifest.json` as the identity and initialization record for this Workspace.
- Keep cloned code Repositories under `repos/`; Lumon does not modify their working trees during initialization.
- Keep runtime outputs under `lumon/runs`, `lumon/artifacts`, `lumon/logs`, and `lumon/tmp`.
- Do not store secrets in this Workspace.
- Global Agent Skills live under `~/.agents/skills/`; do not copy them into this Workspace.
- Use `lumon doctor --workspace <path>` for read-only Workspace checks.
- Add Workspace-specific rules here instead of changing the global Skills.
