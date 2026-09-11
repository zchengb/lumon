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

The Workspace itself continues to contain:

```text
<workspace>/lumon/manifest.json
<workspace>/lumon/workspace.toml
```

The manifest identifies the Workspace. The Workspace TOML records Repository
metadata. User-level settings, including the Feishu Webhook URL, stay in the
corresponding profile and are not copied into the Workspace.

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
