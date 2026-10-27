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
The default Workspace picker labels missing paths and invalid configurations
and disables those options. An unavailable saved default remains selected
until the user explicitly changes it; opening Settings never rewrites it.
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

## Agent conversation trace links

The Agent conversation table includes a **Langfuse** column. **View trace** opens
that execution's private trace in a new tab; Langfuse project access is still
required. Lumon uses the SDK's `get_trace_url` and saves the credential-free URL
with the run, including running, failed and interrupted executions. Changing
the configured endpoint or project does not rewrite historical links.

Project discovery runs off the event loop with a two-second wait limit. Disabled
or unsampled traces and unavailable/invalid links show `—` and never fail the
conversation. Opening history does not query Langfuse, change trace visibility,
or migrate the database. Older runs without a saved mapping also show `—`;
their trace IDs cannot be inferred from Lumon's run IDs.

## Auto Delivery execution history

Available in Lumon 1.4.13, alongside multiline Auto Delivery trigger prompts.

The Auto Delivery page reuses the earlier Dashboard's **Current progress**,
**Delivery history**, and **Scheduler activity** layout. It refreshes every
three seconds while open and supports inspecting a recorded Story or poll.
Running elapsed times tick locally every second without extra API requests.
Only a running Story's active stage shows a sweeping line and spinner; terminal
states stay static and retain their recorded duration. Reduced-motion preferences
disable both animations. The sweep indicates activity, not a completion percentage.
History is scoped to the selected Workspace and shows the Story with its Jira
link, start time, status, and elapsed time such as `12m13s`.
Titles omit the Jira-key prefix and truncate with their full text available on
hover. The Jira key appears in the metadata row below instead of the branch.
Table cells are vertically centered. A final Actions column
offers confirmed deletion of finished history entries. Active work cannot be
deleted. Deletion is Workspace-scoped and soft: `history-deleted.json` hides the
row from Dashboard history across reloads, but retains receipts, notifications,
activity, and duplicate-delivery protection. Jira tasks, code, branches and
worktrees are not deleted. Scheduler poll rows remain unchanged.
Verification, result, and the phase label beneath each history status are not
displayed in this table; persisted receipts and the progress/activity view are
unchanged.

Scheduler activity shows only start time, status, and elapsed time, without a
Result column or a count beside its heading. Status buttons still select a poll
for inspection in the progress/activity view.

Each scheduled poll saves an owner-only `poll.json` under `lumon/runs/<poll-id>`.
Claimed Stories keep the existing `run.json` receipt under their own run ID and
link to their parent with `poll_id`. No eligible Story is an idle poll, not a
successful development result. `activity.json` retains the latest 200 safe
phase/operation summaries. New command events include an expandable redacted command
preview (up to 1 KiB, with a truncation marker), operation ID and exit code.
Configured secrets, common credential/prompt arguments and heredoc bodies are
redacted before persistence; raw stdout/stderr are not stored. Older receipts
remain summary-only and cannot be backfilled from this history. Arbitrary embedded
private data cannot be reliably detected, so commands should never embed sensitive
documents or prompts directly.

The poll prompt tells the Agent to pass `--poll-id` to `lumon delivery start`,
report `implementation`, `verification`, and `handoff` with
`lumon delivery progress`, and record exactly one terminal outcome. A poll that
returns without closing its claimed Story is failed, not reported as completed.
Duplicate starts cannot overwrite a receipt. The existing Workspace poll lock
also guards interrupted-run recovery; recovery never retries work, changes Jira,
or sends notifications. An unknown interruption time remains unknown.

Configure eligibility in the current Workspace's Jira trigger query and delivery
instructions in its execution prompt. Lumon does not add project-specific Jira
rules to presets.

## Workspace flows

### Overview system map

The Overview map places the named Workspace at the center, with Capabilities on
the left, Workflows on the right, and Agent, Auto Scan and Auto Delivery below.
The hub shows the Workspace name and repository count. Filters highlight each
group without hiding the others. Selecting a node opens its details, with an
action to navigate to the related settings or workflow; selecting either catalog
heading opens that catalog. These actions do not start jobs.
The Overview sidebar keeps the Automation panel but omits the Workspace details
section (full ID, creation date and initialization version).
It reads the existing catalog endpoints
on entry and every 15 seconds after the previous catalog request finishes, only
while Overview is mounted and the browser document is visible. Hiding the tab
pauses polling; returning to it refreshes immediately (or waits for an already
in-flight request). Leaving Overview removes the timer and visibility listener.
Catalog polling never starts jobs or reloads repository health and automation
settings; those still follow the existing Overview refresh behavior. Refreshing
Overview also reloads the catalogs. Background refreshes retain the current map;
a failed catalog keeps its last loaded entries with an unavailable indicator
until a later request succeeds. Enabled, disabled, invalid, loading and
unavailable catalog states stay distinct, including a partially unavailable map.
All registered documents remain visible, including unscheduled workflows, with
saved schedule state shown separately. Capability and workflow descriptions are
shown as plain text in their details rather than in each map row. Blank
descriptions show a localized placeholder; no summaries are invented. Common
weekday and minute-interval schedules are shown in local-language form; other
cron expressions remain unchanged, and details retain the saved expression.

Connections indicate Workspace membership, not workflow-to-workflow dependencies
or automatic triggers. Narrow screens stack the groups without diagram wires.
Auto Scan and Auto Delivery retain their separate built-in workflows. The map
shows saved configuration, not process health or verified capability credentials.

The separate **Visual environment** panel reports passive iOS, Android, local Web
browser and Docker prerequisites from the same inspector used by Agent prompts.
It shows tool readiness without displaying runtime status or a verification footer.
Check details are question-mark popovers. **Check environment** refreshes the report
without starting devices or installing dependencies. See
[visual verification](visual-verification.md) for the checks and their limits.
Switching Workspaces discards stale catalog responses. The map supports English,
Simplified Chinese, Traditional Chinese, keyboard navigation and narrow screens.

The Overview **Automation** panel also lists the selected Workspace's saved
workflow schedules, alongside Auto Delivery and Auto Scan. Each row shows the
workflow name, effective enabled/disabled state and cron expression in the local
timezone. Selecting a row opens that workflow and its schedule settings in
**Workflows**. Returning to Overview reloads the saved schedules.

The selected Workflow's schedule controls are integrated into the top of its
Markdown panel, above Preview/Edit content, so long documents cannot hide the
scheduling option. The switch shows the schedule state without a duplicate status
badge. Schedule and Markdown changes retain separate Save actions and draft guards;
editing only the schedule does not enable the Markdown Save button.

**Run now** executes the selected saved Workflow without enabling or changing its
schedule. Disabled, invalid and unsaved Workflow documents cannot be started.
The button shows execution in progress and reports actual completion or failure;
manual and scheduled runs share the same exclusion lock. The schedule's two
explanatory paragraphs are no longer shown. Running a Workflow executes its saved
instructions, including any configured external actions or notifications.

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

The **Settings** page has a Workspace-scoped **Auto Delivery** panel with its own
enable switch and Save button. It stores:

- a credential-free **Jira site** and **Trigger conditions (JQL)** that scope
  eligible Stories, for example project, active sprint, Ready for Dev status and
  the opt-in Flag. Use the actual status IDs behind the board column;
- a multiline **Execution prompt** (up to 8000 characters) describing delivery
  conditions and verification requirements. A Technical Plan is optional;
- a five-field numeric cron **Schedule Expression** (the default is
  `*/5 * * * *`);
- a **Code submission policy**: local uncommitted handoff (default), commit/push
  feature branch, feature branch plus PR, or direct fast-forward push to the target
  branch. An optional target/PR-base override applies to this Workspace; blank
  means each Repository's registered branch, not an assumed main/master.

Schedule, JQL, submission-policy and target-branch guidance is hidden by
default. Click the question-mark button beside a field label to open a floating
tooltip without shifting the form layout. Click again, click outside, or press
Escape to close it; moving focus away, scrolling or resizing also closes it.
Tooltips stay inside the viewport and are not clipped by the panel. Help controls
do not change or save Workspace settings.

When enabled on macOS, saving its timing settings installs or updates an owner-level
LaunchAgent named `com.lumon.delivery.<workspace-id>`. Each scheduled run
executes `lumon delivery poll`. Under the existing Workspace lock, it performs a
read-only Jira search through the authenticated local TWG CLI (no Codex turn).
Search uses `twg jira workitem query` with full JSON output, not an Agent
interpretation of a CLI summary or the removed `twg api` command. Existing
receipts in any state are excluded in the server-side JQL before requesting one
candidate, preserving the configured filter precedence and ordering. Failed or
blocked/stopped cards are not blindly retried. They can be continued explicitly
using Dashboard **Continue**, `lumon delivery resume`, or a post-terminal Jira
status transition back into the configured entry conditions. The stored JQL is unchanged.

### Continue and stop a Delivery

Continue keeps the same logical run ID and isolated worktrees. It archives the
previous receipt as `attempt-N.json`, increments the attempt, refreshes Workspace
instructions/capabilities, and compares saved HEAD/diff fingerprints before reusing
verification. Source changes invalidate the saved verification summary. Old receipts
without a saved Agent session start a new session with the checkpoint; otherwise
the original Codex session is resumed. Only an explicit missing-session preflight
error (before any execution events) falls back to a fresh session and checkpoint;
other errors stop safely, never authorizing repeated external effects. Activity is still bounded; attempt
receipts and checkpoints are durable separately from its 200-entry window.

The Dashboard's **Stop** requests cancellation from the owning worker. **Stopping**
remains visible until the Agent and its process-group children have exited; only
then is the receipt marked **Stopped**. Already completed external actions are not
rolled back. Executions started by an older Lumon version cannot acknowledge this
protocol, so they do not offer a misleading Stop button. Only one execution can
hold the Workspace lock; stale attempt numbers and duplicate starts are rejected.
Shutting down the Dashboard also interrupts continuations owned by that Dashboard.

Feishu lifecycle notifications are deduplicated by delivery, attempt and event.
Continuation sends **Delivery Resumed**, and subsequent outcome notifications
include the attempt number. Repeating a successful notification within the same
attempt does not send another message. Legacy unscoped notification receipts count
only for attempt 1 and remain intact. This does not change the single final
successful Jira result comment policy below.

Without Dashboard, use the current receipt's attempt number:

```sh
lumon delivery resume --workspace /path/to/workspace --run-id delivery-KEY-123 --attempt 1
lumon delivery stop --workspace /path/to/workspace --run-id delivery-KEY-123 --attempt 2
```

Jira re-entry is checked during the existing schedule, without a Codex turn.
It requires Failed/Blocked/Stopped, a complete status changelog with a newer
non-app-account status transition after that attempt finished, and a current
match to the full saved JQL (including any Flag/sprint gates). The JQL must contain
an explicit `status = ...` or `status in (...)` entry gate; status-less queries
remain manual-resume-only. Merely editing a card, keeping it in Ready for Dev,
or reusing an old transition does not resume it. Completed deliveries are never
automatically reopened. Incomplete/denied history fails closed. A legacy receipt
without a terminal timestamp requires manual continuation.
The consumed changelog ID is retained, so that event cannot start another attempt.
Jira cannot distinguish a UI drag from an API write using the same human account;
the execution prompt therefore forbids the Agent from moving a card back to entry
conditions to authorize its own retry. Fully daemonized/reparented or remote jobs
need explicit capability cleanup; Stop does not undo external effects.

The packaged execution prompt now allows only ONE final successful Jira result
comment per logical Delivery, not one per attempt. Blocked, failed, stopped and
rework outcomes are kept locally. The Agent reconciles the stable run marker and
saved comment ID before creating/updating, embeds final media, and reads back the
result. This is an Agent workflow contract, not a security sandbox preventing raw
Jira writes; an ambiguous write must be reconciled rather than blindly retried.

An empty check records an idle poll and makes no Delivery changes. Incomplete,
denied, invalid or timed-out searches record failure, never idle, and never fall
back to Codex. Search is bounded to 30 seconds and one result. If receipt exclusions
exceed the JQL length limit, detection fails instead of silently dropping exclusions. Empty
checks still use Jira API requests, but consume no Codex tokens or Agent quota.
The disabled switch prevents both Jira queries and Agent execution.

Only a new candidate starts a bounded Agent turn with the Workspace's flows and
capabilities, the selected Story and a snapshot of the saved publishing policy.
Before claiming, the Agent must re-read that Story's eligibility, preserve its
Flag and block unclear requirements rather than inventing them. It must not
repeat a backlog scan. The saved publishing policy supersedes older hook wording
about local-only handoff/commits/PRs, but never broadens work beyond this Story.
Development stays in isolated `lumon/delivery-<Story-key>` worktrees, including
direct mode, without changing registered checkouts or unrelated edits.
Published modes require validation, scoped commits, remote read-back and, for PR
mode, a verified PR link. Direct mode never force pushes; a moved/rejected target
must block. No mode authorizes auto-merge, releases or deployment. Missing tools
or credentials fail/block instead of triggering automatic credential repair.

An eligible Story must use the existing Delivery lifecycle commands so
the configured Feishu Webhook receives the normal started, completed, failed,
or blocked notification.

The prompt is saved only for the current Workspace, with its line breaks preserved.
It may be cleared while Auto Delivery is disabled; enabling in Settings requires
the Jira site, query and execution prompt. Older profiles keep their pause state
and acquire neither Jira query assumptions nor publishing permission; their
unconfigured polls fail before starting Codex until a query is configured.
Editing only the query, prompt or submission policy does not reload the job or
interrupt active work. The next poll loads the saved settings. If settings change
during native detection, that check stops before starting an Agent.

The scheduler currently supports interval expressions such as `*/5 * * * *`
and fixed minute/hour expressions such as `0 9 * * 1-5`. The LaunchAgent and
poll lock are owner-only; credentials are never placed in the schedule or poll
output.

## Auto Scan history

The **Settings** page has a separate Workspace-scoped **Auto Scan** panel for its
enable switch, review lookback (1–365 days), five-field cron schedule and completion
hooks. Each automation panel saves independently and preserves drafts in the
other Settings panels. Leaving Settings or switching Workspaces requires confirmation
when any panel has unsaved edits.

The **Completion hooks** field accepts a multiline Agent prompt (up to 8000
characters), saved only for the current Workspace. The review remains read-only;
these instructions run in a separate Agent turn after report generation when
there are findings. Existing hook IDs remain supported through Workspace
capabilities. New Workspaces default to empty hooks (`trigger_hooks = []`), with
no preset completion prompt. Empty hooks keep scans report-only; users opt in by
configuring instructions separately for each Workspace.
An optional [concise Jira Bug template](auto-scan-jira-template.md) provides the
approved three-section Traditional Chinese layout and a traceability footer.
It is selected in the Workspace completion prompt; upgrading Lumon does not
overwrite saved prompts or enable Jira globally. Reused cards retain their content.
Editing this prompt does not reload the scheduled job or interrupt an active scan;
the next scan loads the saved instructions.

The **Auto Scan** page is an execution/history view, with the manual scan action,
and a **Current progress** panel that prioritizes a running scan, otherwise the
latest scan. It uses the same animated stage bars as Auto Delivery, following
the stored Review, Reports and Finalize phases without estimating a percentage
or claiming per-repository progress. The elapsed timer updates every second
while running and freezes on completion; partial and failed scans retain their
warning/error state. Finalize includes configured completion hooks when present.
Visible pages poll every three seconds during a scan or pending manual start,
and every fifteen seconds when idle to discover scheduled/external starts;
hidden/unmounted pages do not poll. Refresh reloads history without starting a
scan, and Run scan now is disabled while a scan is already running.
Recorded failure reasons appear expanded below Current progress, while scan
history retains one row per run. Failed or incomplete scans
without recorded reasons show an explicit unavailable-reason message.
The history retains
one **Scan history** heading, finding counts by
severity (High, Medium, Low in every interface language), and elapsed time as minutes and seconds, such as
`15m34s`. Empty findings and unfinished durations display a dash.
HTML report links display the report directly in a new tab rather than opening
a download dialog. PDF report links retain their download behavior.
An **All issues** panel follows the history, independently of its pagination.
It includes findings from every available scan receipt, keeps the latest record
for each Repository/issue ID, and leaves untracked findings separate. All, Open
(including in-progress, PR-open and reopened), Resolved and Ignored (including
historical `IGNORE` states) filters
show the latest recorded recheck or triage state, not live runtime verification.
Expand **View detail** for location,
impact, trigger, root cause, code, suggestion and source scan; safe
HTTP(S) PR links remain available. Content is plain text, not executable HTML.
An **Ignore** action, after confirmation, saves a Workspace-local triage marker
under `lumon/runs/scans/.ignored/`. The issue remains visible in All and Ignored,
and leaves the Open filter. The marker applies to the same Repository/issue ID
in other receipts, including future scans; untracked findings are occurrence-local.
The scan Agent compares new candidates with all history semantically using root
cause, trigger and affected code paths, including ignored identities. It also
compares non-ignored historical issues for differently worded duplicates.
IDs are storage references, not semantic similarity rules. Validated
same-repository associations are retained in `issue_matches`; history displays one
canonical issue, inheriting any member's manual ignore choice. Only unmatched new
findings contribute to new report counts, notifications and completion hooks.
Historical receipts, reports, notifications and Jira records remain unchanged.
Each scan also requires a fresh configured-branch assessment for every non-ignored
known issue, including resolved issues and issues outside the discovery lookback.
Ignored issues are identity references only: they do not require repair rechecks,
and missing or unsolicited assessments for them do not make a scan incomplete.
An equivalent new candidate stays ignored and is excluded from new-finding hooks.
Evidence-backed fixes update history to Resolved; recurrence reopens resolved
issues, while ignored triage remains ignored. Missing, stale, wrong-branch or
contradictory assessments remain unverified and make the scan incomplete; they
never imply a fix. Incomplete scans do not execute completion hooks. These gates
validate evidence structure and consistency, not the factual truth of Agent reasoning.
Pending saves prevent double submissions; failures leave the issue unchanged and
allow retry. This does not import the old project's separate issue registry or
add resolve/restore actions. Loading failures are not presented as zero issues.
The **Auto Delivery** product label remains English in every interface language.
Its page is also execution-only: live delivery progress, Story history and scheduler
activity remain available, without configuration forms.

## Built-in automation workflows

The built-in rules are separate packaged documents, not Dashboard-editable settings:

- [Auto Scan workflow](../src/lumon/agents/agent/templates/auto_scan.md)
- [Auto Delivery workflow](../src/lumon/agents/agent/templates/auto_delivery.md)

The runtime renders these documents using the saved review lookback, run paths,
poll IDs and custom hooks. Auto Scan's window comes exclusively from `lookback_days`;
there is no hard-coded seven-day window in a workflow description. The old
`workflow_description` profile/API field is retained for compatibility and preserved
by partial updates, but it is no longer displayed, edited or used as review instructions.
Custom Trigger prompts and Completion hooks remain editable in Settings. The built-in
workflow documents are not Workspace library entries and are not exposed in Dashboard.

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
