# Lumon CLI

Lumon is a local, AI-assisted engineering control plane. It provides two connected workflows:

1. **Scan**: examine recent repository change, maintain a durable issue registry, publish reports, and optionally prepare scoped pull requests.
2. **Delivery**: turn an approved Story and technical plan into isolated worktrees, verified changes, pull requests, and an auditable delivery record.

The system is intentionally local-first. Source repositories, configuration, credentials, logs, reports, and Dashboard state remain on the operator's machine unless a configured integration explicitly sends an artifact to Git hosting, Jira, or Feishu.

## Design Principles

- **Explicit authority**: approved Story documents and technical plans govern delivery; raw conversation is not a substitute for them.
- **Isolation**: each Story uses a dedicated feature branch and worktree per affected repository.
- **Evidence**: scan findings, verification results, pull requests, and status transitions are materialized as local records.
- **Minimal intervention**: Lumon changes only the configured workspace and never writes directly to a default branch.
- **Human control**: scheduling and automation are configurable; pull request review and merge remain outside the default automation boundary.

## Installation

### Release installer

```bash
curl -fsSL https://raw.githubusercontent.com/zchengb/lumon-cli/main/get.sh | bash
```

The installer places the executable in `~/.local/bin/lumon` and the supporting library in `~/.lumon/`. `lumen` and `~/.lumen/` remain compatibility aliases for existing workspaces.

### Local checkout

```bash
git clone https://github.com/zchengb/lumon-cli.git
cd lumon-cli
./install.sh
```

Run `lumon doctor` after installation to inspect required and optional local dependencies.

## Workspace Model

Run `lumon init` from an empty project root or an existing documentation repository.

```text
engineering-workspace/
  repos/                       stable repository checkouts
  stories/                     business contracts and technical plans
  standards/                   business, technical, and development loop rules
  AGENTS.md                    persistent agent contract
  lumen/                       local Lumon control plane
    config/                    runtime, repository, and integration configuration
    prompts/
      scan/                    editable scan instructions
      delivery/                editable delivery instructions and coding guideline
    worktrees/                 ephemeral Story worktrees
    results/                   current scan and delivery outputs
    history/                   archived delivery runs
    logs/                      local execution logs
    reports/                   generated HTML and PDF reports
    state/                     issue registry and local Dashboard state
```

`repos/` holds reusable base checkouts. Delivery work never occurs in those base checkouts: it occurs in `lumen/worktrees/<story>/<repository>/`.

## Business and Technical Loop Skills

Install the explicitly invoked, project-scoped workflow skills for Claude Code, Cursor, and Codex:

```bash
lumon skills install --workspace ~/Projects/engineering-workspace --platform all
```

Lumon keeps the canonical packages in `lumen/skills/`; the generated platform adapters are thin pointers. Cursor uses the shared `.agents/skills/` adapter installed by `--platform all`, avoiding duplicate command entries. Existing unmanaged adapter files are preserved unless `--force` is supplied.

## Quick Start

```bash
cd ~/Projects/engineering-workspace
lumon init
lumon doctor
lumon list
```

Lumon records registered workspaces locally. Select the default when working with more than one:

```bash
lumon use <project-slug>
```

## Scan Workflow

The Scan workflow is intended for continuous review of configured repositories. It reads a bounded commit window, asks the configured agent to identify credible issues, persists issue identity across runs, then produces deterministic reports and notifications.

```bash
lumon scan --project <project-slug>
lumon issue list --project <project-slug>
lumon issue ignore ISSUE-<id> --project <project-slug> --reason "Out of scope"
```

Issue decisions are stored in `lumen/state/issue-registry.json`. Ignoring a finding changes only that local registry; it does not modify source code, report history, or remote trackers.

### Scan Scheduling

On macOS, schedules are installed as user-level `launchd` agents.

```bash
lumon schedule scan add --project <project-slug> --cron "0 9 * * 1-5"
lumon schedule scan remove --project <project-slug>
lumon schedule list
```

Supported macOS scan forms are every-N-minutes, daily, and weekday schedules. The Dashboard offers the same configuration through the `AUTO SCAN` view.

## Delivery Workflow

Delivery begins only when a specific Story is business-ready and its technical plan is approved. A Topic is not a delivery unit; split it into concrete Stories first.

```bash
lumon delivery run --story NOVA-101-feature-name
lumon delivery status
```

For an eligible Story, Lumon performs the following sequence:

1. Synchronize the docs repository and configured repositories.
2. Validate Story and technical-plan gates.
3. Create one feature branch and worktree for each affected repository.
4. Move the linked work item into development when Jira integration is enabled.
5. Run the implementation agent with the Story, plan, repository context, and workspace coding guideline.
6. Execute the configured verification profile and, when enabled, bounded remediation.
7. Commit verified changes, publish according to `publish.mode` (`none`, `pr`, `merge`, or `direct`), update delivery metadata, and move the work item to the configured completion state.
8. Archive a delivery snapshot and remove completed worktrees.

Delivery runs are serialized within one workspace because they share control-plane state and verification resources. Multiple completed or paused Story worktrees may coexist.

### Figma design context

For a UI Story with a Figma Design Source, the Technical Loop stores the node ID, a committed design-context snapshot, and an approved reference in the Visual Delivery Contract. Delivery uses the snapshot and reference by default. To let a headless Cursor agent read the live node through an already configured `figma` MCP server, explicitly enable it in `lumen/config/delivery.json`:

```json
{ "execution": { "approve_mcps": true } }
```

This only approves MCP use for a delivery with a Figma contract; it does not install or configure Figma MCP. If the server is unavailable, Delivery continues from the committed snapshot and reference.

### Repository Governance

Dashboard → Repository is the control plane for connected Git repositories. It detects the default branch, Git health, Java and Node versions, and Gradle/Maven/npm/pnpm/yarn tooling. It keeps separate permissions for Auto Scan fixes, Auto Delivery, and Auto Patch; Auto Patch is enabled by default for registered repositories, while the workflow schedule remains separately controllable.

Delivery verification commands are suggested from the detected build. If no repository-specific commands are saved, Delivery selects the matching runtime profile at execution time. Frontend delivery is currently disabled globally, so the Dashboard does not expose web runtime, browser, or credential configuration.

### Delivery Scheduling

```bash
lumon schedule delivery add --project <project-slug> --every 5m
lumon schedule delivery remove --project <project-slug>
```

The scheduler polls for Stories that meet the existing document and Jira eligibility gates. It does not bypass an unapproved technical plan.

## Prompts and Coding Guideline

Workspace prompt fragments are editable and versionable:

```text
lumen/prompts/scan/
lumen/prompts/delivery/
  coding-guideline.md
```

`coding-guideline.md` is copied into every new workspace. Delivery composition prefers this workspace copy, so a team can refine its own coding standard without modifying the global CLI installation. The guideline is injected into every delivery Agent prompt together with the Story, technical plan, and repository context.

Refresh missing defaults without replacing local prompt edits:

```bash
lumon upgrade --project <project-slug>
```

## Interactive Dashboard

```bash
lumon dashboard --project <project-slug>
```

The command starts a local service bound only to `127.0.0.1` and opens the full URL with its dynamically allocated port. Its React interface is prebuilt and packaged with Lumon, so operators do not need Node.js, npm, or frontend dependencies. The Dashboard has four views:

| View | Scope |
|---|---|
| `AUTO SCAN` | scan history, tracked findings, ignore decisions, scan schedule |
| `AUTO DELIVERY` | current run, verification evidence, PR history, delivery polling |
| `PROMPTS` | scan prompts, delivery prompts, workspace coding guideline |
| `SETTINGS` | workspace controls, locally managed integration keys, scan window, and schedules |

Use the exact URL printed by Lumon. `http://127.0.0.1` without a port is not the Dashboard address.

Stop the local Dashboard service when it is no longer needed:

```bash
lumon dashboard stop --project <project-slug>
```

For a read-only artifact without the interactive local server:

```bash
lumon dashboard --project <project-slug> --static
```

## Configuration and Credentials

Workspace configuration is stored under `lumen/config/`. Integration secrets use the workspace-local `lumen/.env.local`, except Web visual-auth credentials, which are stored in the repository runtime config and shown in the local Repository editor for debugging.

```bash
lumon config set-webhook <feishu-webhook-url> --project <project-slug>
lumon config set-cursor-api-key <api-key> --project <project-slug>
lumon config set-gh-token <token> --host <git-host> --project <project-slug>
lumon config set-visual-auth <repository> <credential> --project <project-slug>
lumon config set-scan-window 14 --project <project-slug>
```

Jira integration uses the locally authenticated TWG CLI. Configure it through `lumon config set-jira`; authenticate TWG separately before scheduled or delivery operations.

The Jira project key is configured once in `lumen/config/common.json` under `notifications.jira.project_key` and is shared by Auto Scan, Auto Delivery, and Auto Patch. `lumen/config/delivery.json` only contains Delivery-specific workflow settings such as transition statuses.

### Jira and TWG OAuth token refresh

Lumon does not store Jira credentials. When Jira sync is enabled, it calls the locally installed [TWG CLI](https://developer.atlassian.com/cloud/twg-cli/) using OAuth tokens in `~/.config/twg/auth.conf`.

TWG access tokens are short-lived (typically about one hour). TWG is designed to refresh them automatically with a refresh token. If refresh fails or the session is idle for too long, Jira steps can fail with `AUTH_EXPIRED` even though `twg doctor` passed earlier.

**What Lumon refreshes automatically**

When Jira sync is enabled for the workspace, Lumon runs `twg auth refresh --force` before:

- a scheduled or manual **scan** starts
- a scheduled or manual **delivery** run starts
- the delivery scheduler reads Jira status
- the Dashboard **Retry** action resets a failed delivery in Jira
- post-scan Jira issue creation
- delivery Jira transitions and comments (including at the end of long runs)

If Jira sync is disabled in `config/common.json` or `config/delivery.json`, Lumon skips the refresh call.

**What you should configure on the machine**

Enable TWG background upkeep so tokens stay fresh during long scan or delivery runs (often 30–60+ minutes):

```bash
twg upkeep enable
twg auth refresh --force
twg doctor
```

Upkeep runs on a per-user schedule and refreshes OAuth credentials before they expire. Lumon’s start-of-run refresh does not replace upkeep for runs that stay active longer than one access-token lifetime.

**When re-login is required**

Refresh tokens eventually require interactive re-authentication, for example after roughly 30 days without use or if the credential is revoked. In that case:

```bash
twg login --force
twg doctor
```

There is no permanent “forever” personal access token for TWG. For fully headless automation outside a logged-in user session, use your organization’s TWG OAuth service-account setup ([Atlassian docs](https://support.atlassian.com/organization-administration/docs/configure-oauth-2-1-for-teamwork-graph-cli/)).

**Manual refresh**

```bash
python3 ~/.lumen/lib/scripts/jira_sync.py refresh --scan-workspace <workspace>/lumen
python3 ~/.lumen/lib/scripts/jira_sync.py refresh --delivery-workspace <workspace>/lumen
```

These commands refresh only when Jira sync is enabled for that workspace.

## Command Reference

| Command | Purpose |
|---|---|
| `lumon init [dir]` | Initialize an integrated Scan and Delivery workspace |
| `lumon register [dir]` | Register an existing workspace |
| `lumon list`, `lumon use <slug>` | Inspect and select local workspaces |
| `lumon scan` | Run one review cycle |
| `lumon issue list`, `lumon issue ignore` | Inspect and govern tracked findings |
| `lumon schedule` | Manage Scan and Delivery schedules |
| `lumon delivery run --story <story>` | Execute one approved Story |
| `lumon delivery status` | Show latest delivery progress and evidence |
| `lumon skills install --workspace <path> --platform all` | Install explicit Business and Technical Loop skills |
| `lumon dashboard` | Open the interactive local control plane |
| `lumon upgrade` | Update CLI and refresh missing workspace defaults |

## Operational Boundary

Lumon does not automatically merge pull requests or deploy to production. CI/CD monitoring and deployment automation can be layered on later, but they are intentionally outside the default local execution path.
