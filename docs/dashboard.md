# Lumon Dashboard

## Start

The Dashboard is a local-only Python API with a bundled React frontend:

```text
lumon ui
lumon ui --no-open
lumon ui --port 8080
lumon ui --workspace /path/to/lumon-workspace
```

The server always binds to `127.0.0.1`. Port `0` (the default) means Lumon
selects an available local port. The installed Wheel contains the compiled
frontend, so Node is only needed when developing or building the package.

## Workspace registry

Lumon keeps the machine-local Workspace list outside the Workspace directory:

```text
~/.lumon/
├── registry.toml
└── workspaces/
    └── <workspace-id>/
        └── config.toml
```

Set `LUMON_HOME` to use another user-state root, for example in tests. The
registry contains only Workspace IDs, names, paths, and registration times.
`lumon init` registers a successfully initialized Workspace automatically.
The Dashboard can explicitly register an existing Workspace; v1 does not scan
the home directory or any fixed directory.

On the onboarding page, use **Choose folder** to open the local native folder
selector and populate the Workspace path with an absolute path. Manual path
entry remains available as a fallback. The macOS build uses the system folder
selector; unsupported environments show an actionable error instead of
silently returning a browser-relative path.

The Workspace itself continues to contain:

```text
<workspace>/lumon/manifest.json
<workspace>/lumon/workspace.toml
```

The manifest identifies the Workspace. The Workspace TOML records Repository
metadata. User-level settings, including the Feishu Webhook URL, stay in the
corresponding profile and are not copied into the Workspace.

Manage registrations from the CLI:

```text
lumon workspace list
lumon workspace set-default <workspace-id-or-path>
lumon workspace set-default --clear
lumon workspace remove <workspace-id-or-path>
lumon workspace remove <workspace-id-or-path> --delete
```

`workspace remove` clears Mark's default when the target is selected, then
unregisters the Workspace and removes its user-level profile. It keeps the
Workspace directory unless `--delete` is supplied, and it asks for confirmation
before changing the registry or default selection.

## Global Agent settings

The **Mark Agent** page manages configuration that applies to the local Agent
across all Workspaces: enabled state, Codex model, reasoning effort, default
Workspace, Feishu App credentials, and Langfuse Cloud observability.

The API returns only credential presence flags. New or replacement secrets are
accepted by the update endpoint but never returned to the browser. Lumon saves
them in `$LUMON_HOME/agent.toml` (normally `~/.lumon/agent.toml`) with owner-only
file mode `600`. Environment variables `LANGFUSE_PUBLIC_KEY` and
`LANGFUSE_SECRET_KEY` continue to override saved Langfuse values.
Langfuse content capture is always enabled when observability is enabled. Lumon
redacts credentials client-side before sending prompt and response content, and
the Dashboard does not expose a content capture switch.


Saving the page updates the on-disk configuration. Restart Mark with
`lumon agent stop` and `lumon agent start --background` for the running process
to load the new settings.

## Feishu Webhook

The Settings page supports:

- enabling or disabling Feishu notifications;
- saving a new HTTPS Webhook URL;
- sending a test message without saving a draft URL.

The API returns only whether a URL is configured and a display-safe masked
value that keeps the URL structure plus a short token prefix and suffix. The
profile file is created with owner-only permissions. Future settings such as
Auto Delivery must be introduced as typed settings domains with their own
validation and UI; v1 has no arbitrary key-value editor.

## Build the frontend

From the repository root:

```text
npm --prefix dashboard-ui ci
npm --prefix dashboard-ui run typecheck
npm --prefix dashboard-ui run test
npm --prefix dashboard-ui run build
```

The build writes static assets to
`src/lumon/dashboard/static/`. GitHub Actions runs this build before `uv
build`, so the release Wheel is self-contained and does not require Node at
runtime.

## Interface language

The Dashboard supports English, Simplified Chinese, and Traditional Chinese.
Use the language selector in the top bar, or in the onboarding card before a
Workspace has been registered. The selected language is stored in the current
browser's local preferences and applies to the Dashboard UI, status messages,
confirmation prompts, and date formatting; it is not Workspace business
configuration.
