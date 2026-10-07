# Lumon Dashboard

## Start

The Dashboard is a local-only Python API with a bundled React frontend:

```text
lumon ui
lumon ui --no-open
lumon ui --port 8080
lumon ui --workspace /path/to/lumon-workspace
```

The server always binds to `127.0.0.1`, using the fixed default port `15778`.
Use `--port` to override it; `--port 0` selects an available local port.
An occupied port produces an error instead of silently changing the address.
The installed Wheel contains the compiled frontend, so Node is only needed
when developing or building the package.

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

`workspace remove` clears Agent's default when the target is selected, then
unregisters the Workspace and removes its user-level profile. It keeps the
Workspace directory unless `--delete` is supplied, and it asks for confirmation
before changing the registry or default selection.

## Global Agent settings

The **Settings** page manages configuration that applies to the local Agent
across all Workspaces: enabled state, Codex model, reasoning effort, default
Workspace, Feishu App credentials, and Langfuse Cloud observability.
The model picker loads `GET /api/agent/models` when the page opens. Its refresh
button queries the local Codex CLI's `model/list` catalog again without starting
an Agent turn or changing saved settings. Reasoning choices come from each
model's supported efforts. Switching models retains a compatible effort or
selects the new model's default effort; neither value is persisted until Save.

The catalog depends on the installed Codex version and its account/provider
configuration, not a hard-coded Lumon model list. Refreshing does not upgrade
Codex or guarantee account access to every listed model. A saved model that is
absent from the catalog, or a failed catalog request, never overwrites the
current selection. Model discovery errors leave the rest of Settings usable.

The Agent provider field also checks `GET /api/agent/codex-status` for **Codex CLI** updates.
When an update is available, it shows the installed version and **Update available**
badge inline with **codex** inside the provider field, leaving the model picker
without a separate CLI status line. Model descriptions, executable
paths, upgrade instructions, and extra update controls are omitted. No notice is
shown while checking, when the CLI is current, or when a check cannot complete.
The check uses Lumon's normal PATH resolver; a standalone installation can shadow
the newer app-bundled CLI. This is separate from Lumon package updates and never
installs software, changes models, or restarts jobs.

Release metadata comes from the official `@openai/codex` npm package's `latest`
endpoint without account credentials. Successful checks are cached for ten
minutes and failed checks for one minute. **Refresh models** bypasses that cache.
The installed version is always read again. Timeouts, invalid metadata, and
unavailable CLIs remain unknown/unavailable in the API without blocking model
choice or Settings. Prereleases ahead of the stable release do not prompt a downgrade.
After upgrading the CLI, refresh models; account/provider rollout can still
limit model availability.

The API returns credential presence flags and short prefix/suffix masks. New or
replacement secrets are accepted by the update endpoint but never returned in
full. Lumon saves them in `$LUMON_HOME/agent.toml` (normally
`~/.lumon/agent.toml`) with owner-only file mode `600`. Environment variables
`LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` continue to override saved
Langfuse values.

Langfuse content capture is always enabled when observability is enabled. Lumon
redacts credentials client-side before sending prompt and response content, and
the Dashboard does not expose a content capture switch.

Agent and Langfuse each have a Save button inside their panel. Each button saves
only that panel's edits; unsaved edits in the other panel are preserved. Both
buttons are disabled while a save is pending to serialize updates to the shared
configuration. A failed save keeps the draft available for retry.

Saving a panel updates the on-disk configuration. Model and reasoning effort
changes apply automatically when the next request starts, including queued turns
and resumed conversations. Requests already in progress keep their original
settings. Other settings, including Feishu credentials, the default Workspace,
and Langfuse configuration, still require `lumon agent stop` followed by
`lumon agent start --background`.

## Auto Delivery execution history

Available in Lumon 1.4.13, alongside multiline Auto Delivery trigger prompts.

The Auto Delivery page reuses the earlier Dashboard's **Current progress**,
**Delivery history**, and **Scheduler activity** layout. It refreshes every
three seconds while open and supports inspecting a recorded Story or poll.
History is scoped to the selected Workspace and shows Jira links, phase,
verification, PR/result, and elapsed time such as `12m13s`.

Each scheduled poll saves an owner-only `poll.json` under `lumon/runs/<poll-id>`.
Claimed Stories keep the existing `run.json` receipt under their own run ID and
link to their parent with `poll_id`. No eligible Story is an idle poll, not a
successful development result. `activity.json` retains the latest 200 safe
phase/operation summaries; prompts, command lines, and raw output are excluded.

The poll prompt tells the Agent to pass `--poll-id` to `lumon delivery start`,
report `implementation`, `verification`, and `handoff` with
`lumon delivery progress`, and record exactly one terminal outcome. A poll that
returns without closing its claimed Story is failed, not reported as completed.
Duplicate starts cannot overwrite a receipt. The existing Workspace poll lock
also guards interrupted-run recovery; recovery never retries work, changes Jira,
or sends notifications. An unknown interruption time remains unknown.

Configure eligibility and delivery authorization in the current Workspace's
trigger prompt. Lumon does not add project-specific Jira rules to presets.

## Workspace flows

The Overview **Automation** panel also lists the selected Workspace's saved
workflow schedules, alongside Auto Delivery and Auto Scan. Each row shows the
workflow name, effective enabled/disabled state and cron expression in the local
timezone. Selecting a row opens that workflow and its schedule settings in
**Workflows**. Returning to Overview reloads the saved schedules.

Workflows without a saved schedule, deleted workflows and invalid Markdown files
are omitted. Saved disabled schedules remain visible; a disabled workflow never
appears enabled even when its saved schedule flag is still set. This is a
read-only configuration summary, not a check of launchd job health, and does not
install, reload or start any jobs.

The **Flows** page edits Markdown files under the selected Workspace's
`lumon/flows/` directory. The list shows enabled and disabled valid flows as
well as validation errors for files that Agent will ignore. The editor supports
creating, updating, and deleting flow files. **New flow** starts with a design
template; Workspaces do not receive a product-specific flow during initialization.

The Dashboard and Agent use the same files, so saving a flow does not require a
second synchronization step. Agent receives only each enabled flow's ID, brief,
and relative file path in its initial prompt. It reads the full Markdown body
after selecting a flow. A resumed Codex session receives a
fresh brief list on every turn, so Dashboard edits are picked up without
restarting the Agent.

## Feishu Webhook

The Settings page supports:

- enabling or disabling Feishu notifications;
- saving a new HTTPS Webhook URL;
- sending a test message without saving a draft URL.

The API returns only whether a URL is configured and a display-safe masked
value that keeps the URL structure plus a short token prefix and suffix. The
profile file is created with owner-only permissions. Future settings such as
Auto Delivery are exposed as typed settings with their own validation rather
than an arbitrary key-value editor.

## Auto Delivery

The **Auto Delivery** page controls the current Workspace's scheduled delivery
poll. It stores:

- a multiline **Trigger prompt** (up to 8000 characters) describing which
  approved Stories to check, delivery conditions, and verification requirements.
  Existing hook IDs such as the default `jira.delivery_ready` remain supported;
- a five-field numeric cron **Schedule Expression** (the default is
  `*/5 * * * *`).

When enabled on macOS, saving the page installs or updates an owner-level
LaunchAgent named `com.lumon.delivery.<workspace-id>`. Each scheduled run
executes `lumon delivery poll`, loads the Workspace's enabled flows and
capabilities, and gives the configured prompt to one bounded Agent turn. A poll
that finds no eligible event returns `AUTO_DELIVERY_IDLE` and makes no Delivery
changes. An eligible event must use the existing Delivery lifecycle commands so
the configured Feishu Webhook receives the normal started, completed, failed,
or blocked notification.

The prompt is saved only for the current Workspace, with its line breaks preserved.
It may be cleared while Auto Delivery is disabled; enabling requires a prompt or
legacy hook ID. Editing only the prompt does not reload the scheduled job or
interrupt an active poll; the next poll loads the saved instructions.

The scheduler currently supports interval expressions such as `*/5 * * * *`
and fixed minute/hour expressions such as `0 9 * * 1-5`. The LaunchAgent and
poll lock are owner-only; credentials are never placed in the schedule or poll
output.

## Auto Scan history

The **Completion hooks** field accepts a multiline Agent prompt (up to 8000
characters), saved only for the current Workspace. The review remains read-only;
these instructions run in a separate Agent turn after report generation when
there are findings. Existing hook IDs remain supported through Workspace
capabilities. New Workspaces default to empty hooks (`trigger_hooks = []`), with
no preset completion prompt. Empty hooks keep scans report-only; users opt in by
configuring instructions separately for each Workspace.
Editing this prompt does not reload the scheduled job or interrupt an active scan;
the next scan loads the saved instructions.

The **Auto Scan** page shows one **Scan history** heading, finding counts by
severity (High, Medium, Low), and elapsed time as minutes and seconds, such as
`15m34s`. Empty findings and unfinished durations display a dash.
HTML report links display the report directly in a new tab rather than opening
a download dialog. PDF report links retain their download behavior.
The **Auto Delivery** product label remains English in every interface language.

Opening scan history or starting the next scan reconciles abandoned `running`
receipts under the same exclusive Workspace scan lock. If a scan still holds the
lock, history leaves it untouched. Abandoned runs become failed with an interruption
reason; existing findings and artifacts are preserved. An unknown interruption
time remains unknown, so elapsed time displays a dash. Recovery never restarts
reviews, runs completion hooks, sends Webhooks, or reloads schedules.

Focus styles are shared globally: text fields, dropdowns, and Markdown editors
use a graphite border and a single soft ring. Keyboard-focused buttons, links,
switches, and scroll regions use a visible graphite outline. Focus is immediate,
and high-contrast mode uses the system highlight color.

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
