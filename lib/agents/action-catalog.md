# Lumon Action Catalog

Read this file before emitting an `ACTION_REQUEST` when the current turn needs
a host action. The `action` value must be copied exactly from the canonical
name column. Do not invent names, translate names, or use compatibility aliases
in a new request. The host still enforces role ownership, authorization, and
resource boundaries.

## Request envelope and parameter rules

Every host action must use this envelope:

```text
<ACTION_REQUEST>{"action":"canonical.action","arguments":{...},"resource":{}}</ACTION_REQUEST>
```

- `action` is copied exactly from the **Canonical action** column. Never use a
  display name, translation, guessed name, or compatibility alias.
- Put every model-selected input in `arguments`. Use the exact field names and
  JSON types shown below; keep `resource` as `{}` unless an action recipe
  explicitly says otherwise.
- `resource` is host scope/context, not a second place to invent parameters.
  Moving a missing field there does not make an invalid request valid.
- `one of A, B` means provide exactly one of those fields. Prefer the first
  field listed; the remaining names are compatibility inputs accepted by the
  host.
- `required` means the field must be present before execution. Adapter config
  such as the project workspace or Jira site may still be supplied by the host.
- Do not send identity fields such as `actor`, `agent_id`, `chat_id`,
  `thread_id`, or `trace_id`; the host fills them.
- If a required value is absent, emit a `CLARIFICATION_REQUEST` instead of
  inventing a field or value.

The JSON inside the envelope is parsed as JSON, not as a shell command. Lists
must be JSON arrays and booleans must be JSON booleans. The examples below are
copyable request shapes; replace only the business values.

## Execution lanes

Use the lowest-risk lane that completes the current turn:

1. **Autonomous read lane** — for read-only Jira evidence, use the directly
   authorized TWG commands below when available. They do not create an
   `ACTION_REQUEST`, and the Harness permission profile allows only
   these two Jira read verbs:

   ```text
   twg jira workitem get <JIRA-KEY> -o json [--site <configured-site>]
   twg jira workitem query --jql 'project = MBPAS AND issuetype = Story' --limit 20 -o json [--site <configured-site>]
   ```

   Use the current workspace/project Jira configuration and do not read TWG
   auth files or secrets. If a configured Jira site is required, read the
   non-secret workspace config and pass its site value; never invent one. Never
   run other TWG verbs, arbitrary shell, HTTP, Python, or GUI commands. If the
   authorized command is unavailable or fails, use the canonical host read
   action as the fallback.

2. **Host-gated mutation lane** — Jira create/update and every external,
   irreversible, identity-sensitive, or audited mutation must use the exact
   `ACTION_REQUEST` recipe below. A successful read is not permission to write.

3. **Workspace lane** — ordinary project-file investigation may use the
   read/edit capabilities explicitly granted by the current Harness profile;
   read `.lumon/blacklist.md` before using them.

## Feishu conversation capabilities

These capabilities let the Agent choose when the user should receive an
intermediate update or an attachment. The Host performs the actual Feishu API
call with the current Agent's credentials and source message, then returns a
receipt to the same provider session.

| Canonical action | Purpose | `arguments` fields |
| --- | --- | --- |
| `feishu.send_progress` | Send a concise visible milestone, finding, blocker, or next step in the current Feishu conversation. | required: `message`; optional: `phase` |
| `feishu.send_file` | Upload a workspace file and attach it to the current Feishu conversation. | required: `path`; optional: `caption`, `cleanup` |

Rules:

- Put the file path in `arguments.path`, relative to the current workspace when
  possible. Absolute paths are accepted only when they resolve inside that
  workspace. Do not provide identity, chat, thread, or workspace context; the
  Host injects those fields from the trusted inbound message.
- Only regular workspace files may be attached. Secret-like files (for
  example `.env`, private-key files, and certificate bundles) are rejected.
- Generated PDF transfer artifacts under `output/pdf/` are cleaned up after a
  successful upload by default. Use `cleanup=true` only for another generated
  PDF under that same directory; source documents are never deleted by this
  action.
- A successful receipt means the Host uploaded and attached the file. Do not
  claim that a file was sent from a path alone. If the receipt is failed or
  denied, explain the blocker and do not retry the same action indefinitely.
- Progress updates should describe evidence, a blocker, a next step, or a
  question. They are not a transcript of private reasoning or raw provider
  tool output. Keep each update focused so the thread reads naturally.

Send a progress update and continue the same request:

```text
<ACTION_REQUEST>{"action":"feishu.send_progress","arguments":{"phase":"Evidence","message":"我已完成 Jira 與工作區核對，接下來檢查輸出文件。"},"resource":{}}</ACTION_REQUEST>
```

Attach an explicitly requested generated PDF:

```text
<ACTION_REQUEST>{"action":"feishu.send_file","arguments":{"path":"output/pdf/MBPAS-1437-technical-plan.pdf","caption":"Technical Plan PDF 已生成，现附上文件。"},"resource":{}}</ACTION_REQUEST>
```

## Delegation and jobs — Milchick

| Canonical action | Purpose | `arguments` fields |
| --- | --- | --- |
| `agent.job.create` | Durable/background delegation or compatibility path; simple thread handoffs use visible `@Agent` collaboration when enabled. | required: `target_agent`, `capability`; optional: `issue_key`, `story`, `depends_on` (array), `execute` (boolean) |
| `agent.job.list` | List jobs for the current project. | optional: `limit` (number) |
| `agent.job.show` | Show one job and its parent summary. | required: `job_id` |
| `agent.job.cancel` | Cancel an existing job. | required: `job_id` |
| `agent.job.retry` | Retry an existing child job. | required: `job_id` |
| `agent.list` | List registered Agents. | none |
| `agent.health` | Read registered Agent health/status. | none |

For delegation, emit one `agent.job.create` request and wait for its host
receipt before claiming that work was assigned or started.

Any Agent may also use the lightweight `agent.delegate` capability when a
native Host Tool is available. It uses the same `target_agent` and `capability`
fields, is resolved by the Host, and returns an Action Receipt; it is not a
license to impersonate the target Agent or bypass user/chat authorization.

## Jira — direct read lane first; mutations through the host adapter

| Canonical action | Purpose | `arguments` fields |
| --- | --- | --- |
| `jira.workitem.get` | Host fallback for reading one Jira work item when the authorized TWG read command is unavailable or fails. | required: one of `issue_key`, `id`, `key`; prefer `issue_key` |
| `jira.workitem.query` | Host fallback for querying Jira when the authorized TWG read command is unavailable or fails. | required: `jql`; optional: `limit` (number), `project_key`, `board_id`, `site` |
| `jira.sprint.untested.report` | Read the untested Story report. | optional: `standard` (`A`/`B`/`C`/`D`), `statuses` (array) |
| `jira.workitem.create` | Create a Jira work item after the request calls for it. | required: `summary`; optional: `description`, `project_key`, `issue_type`, `target_version`, `priority`, `labels` (array), `parent` |
| `jira.workitem.update` | Update an existing Jira work item. | required: `issue_key`; plus at least one of `summary`, `description`, `priority`, `labels` (array), `add_labels` (array), `comment`, `status` |

## Operations and test-case ownership

| Canonical action | Purpose | `arguments` fields |
| --- | --- | --- |
| `test_case.generate` | Mark-owned test-case generation that writes the configured Sheet. Milchick delegates this capability. | required: one of `issue_key`, `story`, `story_id`, `scope`; use `scope="ready_for_qa"` for all matching Stories; optional: `statuses` (array) |
| `project.status` | Read lightweight project status. | none |
| `workflow.status` | Read lightweight workflow status. | none |
| `schedule.status` | Read lightweight schedule status. | none |
| `lumen.system.health` | Read system health when host access allows it. | none |
| `lumen.agent.status` | Read Agent runtime status when host access allows it. | none |
| `lumen.runner.status` | Read runner status when host access allows it. | none |

## Mark delivery and loops

| Canonical action | Purpose | `arguments` fields |
| --- | --- | --- |
| `delivery.readiness` | Read delivery readiness. | required: `story` |
| `delivery.status` | Read delivery status. | optional: `story`, `run_id` |
| `delivery.result` | Read a delivery result. | required: `run_id` |
| `delivery.start` | Start delivery for an approved Story. | required: one of `story`, `story_id`, `issue_key`; prefer `story` |
| `delivery.cancel` | Cancel a delivery run. | required: one of `run_id`, `story`, `story_id`; prefer `run_id` |
| `delivery.quick_change` | Run a bounded source change. | required: `repository` (string), `target_files` (array), `request` (string); optional: `target_version`, `change_type` |
| `loop.business` | Start the Business Loop. | none |
| `loop.technical` | Start the Technical Loop. | required: one of `issue_key`, `story`, `story_id`; prefer `issue_key` |
| `story.read` | Read Story context. | required: `story` |
| `technical_plan.read` | Read a Technical Plan. | required: `story` |

## Dylan risk and scan

| Canonical action | Purpose | `arguments` fields |
| --- | --- | --- |
| `risk.read` | Read risk findings. | required: one of `project`, `finding_id`; optional: `limit` (number) |
| `risk.resolve` | Resolve a risk finding. | required: `finding_id`; optional: `basis`, `reason`, `override` (boolean) |
| `risk.mark_remediated` | Mark a finding remediated. | required: `finding_id`; optional: `reason` |
| `risk.reconcile` | Reconcile project risk state. | required: `project` |
| `scan.read` | Read scan results. | required: one of `project`, `finding_id`; optional: `limit` (number) |
| `scan.schedule.read` | Read scan schedule. | required: `project` |
| `scan.schedule.update` | Update scan schedule. | required: `project`, `cron` |
| `scan.verify.request` | Request scan verification. | required: `finding_id` |

## Canonical request recipes

### Delegate a Technical Plan

Use the canonical action name and put the routing fields in `arguments`:

```text
<ACTION_REQUEST>{"action":"agent.job.create","arguments":{"target_agent":"mark","capability":"loop.technical","issue_key":"MBPAS-1503"},"resource":{}}</ACTION_REQUEST>
```

`target_agent` is an Agent ID, not a person display name. `capability` is the
target Agent's canonical capability, not a natural-language description. For
this workflow, `mark` + `loop.technical` is the valid Technical Plan handoff.
After emitting this request, wait for the host receipt before saying the job
was assigned or started.

Do **not** emit either of these shapes:

```text
<ACTION_REQUEST>{"action":"create_job","arguments":{"agent":"Mark","task":"Technical Plan"}}</ACTION_REQUEST>
<ACTION_REQUEST>{"action":"agent.job.create","resource":{"target_agent":"mark","capability":"loop.technical"}}</ACTION_REQUEST>
```

The first uses a compatibility alias and invented field names; the second puts
model inputs in the wrong object. Both are avoidable when this catalog is read.

### Common action shapes

Generate test cases for every Ready for QA Story:

```text
<ACTION_REQUEST>{"action":"test_case.generate","arguments":{"scope":"ready_for_qa"},"resource":{}}</ACTION_REQUEST>
```

Start or cancel delivery:

```text
<ACTION_REQUEST>{"action":"delivery.start","arguments":{"story":"MBPAS-1503"},"resource":{}}</ACTION_REQUEST>
<ACTION_REQUEST>{"action":"delivery.cancel","arguments":{"run_id":"run-123"},"resource":{}}</ACTION_REQUEST>
```

Run a bounded source change; `target_files` is a JSON array:

```text
<ACTION_REQUEST>{"action":"delivery.quick_change","arguments":{"repository":"lumon","target_files":["lib/agents/action-catalog.md"],"request":"Document the canonical action argument contract","change_type":"documentation"},"resource":{}}</ACTION_REQUEST>
```

Start a Technical Loop directly:

```text
<ACTION_REQUEST>{"action":"loop.technical","arguments":{"issue_key":"MBPAS-1503"},"resource":{}}</ACTION_REQUEST>
```

Read or update Jira:

```text
<ACTION_REQUEST>{"action":"jira.workitem.get","arguments":{"issue_key":"MBPAS-1503"},"resource":{}}</ACTION_REQUEST>
<ACTION_REQUEST>{"action":"jira.workitem.query","arguments":{"jql":"project = MBPAS AND issuetype = Story","limit":20},"resource":{}}</ACTION_REQUEST>
<ACTION_REQUEST>{"action":"jira.workitem.update","arguments":{"issue_key":"MBPAS-1503","comment":"Technical Plan requested"},"resource":{}}</ACTION_REQUEST>
```

Read or mutate a risk finding:

```text
<ACTION_REQUEST>{"action":"risk.read","arguments":{"finding_id":"finding-123"},"resource":{}}</ACTION_REQUEST>
<ACTION_REQUEST>{"action":"risk.mark_remediated","arguments":{"finding_id":"finding-123","reason":"Fix verified"},"resource":{}}</ACTION_REQUEST>
```

Read or update the scan schedule:

```text
<ACTION_REQUEST>{"action":"scan.schedule.read","arguments":{"project":"mbpas"},"resource":{}}</ACTION_REQUEST>
<ACTION_REQUEST>{"action":"scan.schedule.update","arguments":{"project":"mbpas","cron":"0 2 * * *"},"resource":{}}</ACTION_REQUEST>
```

For `agent.job.show`, `agent.job.cancel`, and `agent.job.retry`, pass the job
identifier as `arguments.job_id`. For actions marked `none`, send an empty
`arguments` object. Read operations still need their listed target; do not
replace a missing target with a guessed project, Story, or finding.

## Compatibility aliases — host normalization only

These are accepted only as a defensive compatibility layer. Do not emit them
from a new model response; always use the canonical name above.

| Non-canonical input | Canonical action |
| --- | --- |
| `job.create` | `agent.job.create` |
| `create_job` | `agent.job.create` |
| `job.list` | `agent.job.list` |
| `job.show` | `agent.job.show` |
| `job.cancel` | `agent.job.cancel` |
| `job.retry` | `agent.job.retry` |
| `jira.testcase.generate` | `test_case.generate` |
| `testcase.generate` | `test_case.generate` |

# Thread-native Agent collaboration

When the workspace `config/common.json` enables
`agent_collaboration.thread_native_handoff`, ordinary Agent-to-Agent
conversation is carried by visible Feishu thread messages.  Use an exact
mention such as `@Mark` and keep the request/evidence in that message; the
Host records it and wakes the mentioned Agent.  Do not invent a Job ID, a
`[LUMEN HANDOFF]` envelope, or a `waiting_user` state for this path.  A direct
human reply to an Agent message resumes only that Agent's provider session.

`agent.job.create` remains the compatibility action for durable background
orchestration and for workspaces where thread-native collaboration is disabled.
