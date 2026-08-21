# Agent World

Lumon runs provider processes inside an OS-enforced Agent World. The Host
creates a disposable workspace, a service HOME, and a private temporary
directory; the provider process crosses the boundary through one adapter:

```text
Feishu ingress
    -> Host entry gate
    -> SessionHost
    -> DisposableWorkspace + AgentWorld
    -> Cursor / OpenCode / Codex subprocess
    -> guarded publish receipt
```

The canonical checkout is Host-only. Provider processes receive a copy and may
write it freely. A successful turn is published through the existing
workspace mutation gate; deletes, copies, and renames that do not originate in
the disposable layer are rejected.

On macOS the default backend is `sandbox-exec` with network access enabled.
Container/VM and dedicated Unix identities are adapter options, not provider
features. `sandbox-exec` enforces path and process access but does not change
the Unix UID; `lumen agent-world status` reports that distinction explicitly.

Useful checks:

```bash
lumen agent-world status --agent mark --provider codex
lumen agent-world provision --agent mark --provider codex
lumen agent-world certify --agent mark --provider codex --live
```

Provisioning creates an empty service identity. Lumon never copies a personal
`~/.codex`, Cursor, `twg`, or GitHub credential file into that identity.
