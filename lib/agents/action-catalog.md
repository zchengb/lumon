# Lumon Action Catalog

Read this file before emitting an `ACTION_REQUEST` when the current turn needs
a host action. The `action` value must be copied exactly from the canonical
name column. Do not invent names, translate names, or use compatibility aliases
in a new request. The host still enforces role ownership, authorization, and
resource boundaries.

Required fields below are the minimum fields checked before execution. Other
fields may be required by the owning adapter or the current workflow.

## Delegation and jobs — Milchick

| Canonical action | Purpose | Required fields |
| --- | --- | --- |
| `agent.job.create` | Delegate work to another Agent; use `target_agent=mark` and `capability=loop.technical` for a Technical Plan. | `target_agent`, `capability` |
| `agent.job.list` | List jobs for the current project. | none; optional `limit` |
| `agent.job.show` | Show one job and its parent summary. | `job_id` |
| `agent.job.cancel` | Cancel an existing job. | `job_id` |
| `agent.job.retry` | Retry an existing child job. | `job_id` |
| `agent.list` | List registered Agents. | none |
| `agent.health` | Read registered Agent health/status. | none |

For delegation, emit one `agent.job.create` request and wait for its host
receipt before claiming that work was assigned or started.

## Jira — available through the host adapter

| Canonical action | Purpose | Required fields |
| --- | --- | --- |
| `jira.workitem.get` | Read one Jira work item. | one of `issue_key`, `id`, `key` |
| `jira.workitem.query` | Query Jira work items. | `jql` |
| `jira.sprint.untested.report` | Read the untested Story report. | none |
| `jira.workitem.create` | Create a Jira work item after the request calls for it. | `summary` |
| `jira.workitem.update` | Update an existing Jira work item. | `issue_key` |

## Milchick operations

| Canonical action | Purpose | Required fields |
| --- | --- | --- |
| `test_case.generate` | Generate test cases and write the configured Sheet. | one of `issue_key`, `story`, `story_id`, `scope` |
| `project.status` | Read lightweight project status. | none |
| `workflow.status` | Read lightweight workflow status. | none |
| `schedule.status` | Read lightweight schedule status. | none |
| `lumen.system.health` | Read system health when host access allows it. | none |
| `lumen.agent.status` | Read Agent runtime status when host access allows it. | none |
| `lumen.runner.status` | Read runner status when host access allows it. | none |

## Mark delivery and loops

| Canonical action | Purpose | Required fields |
| --- | --- | --- |
| `delivery.readiness` | Read delivery readiness. | none |
| `delivery.status` | Read delivery status. | none |
| `delivery.result` | Read a delivery result. | none |
| `delivery.start` | Start delivery for an approved Story. | one of `story`, `story_id`, `issue_key` |
| `delivery.cancel` | Cancel a delivery run. | one of `run_id`, `story`, `story_id` |
| `delivery.quick_change` | Run a bounded source change. | one of each: repository, target files, request |
| `loop.business` | Start the Business Loop. | none |
| `loop.technical` | Start the Technical Loop. | one of `issue_key`, `story`, `story_id` |
| `story.read` | Read Story context. | adapter/workflow dependent |
| `technical_plan.read` | Read a Technical Plan. | adapter/workflow dependent |

## Dylan risk and scan

| Canonical action | Purpose | Required fields |
| --- | --- | --- |
| `risk.read` | Read risk findings. | none |
| `risk.resolve` | Resolve a risk finding. | `finding_id` |
| `risk.mark_remediated` | Mark a finding remediated. | `finding_id` |
| `risk.reconcile` | Reconcile project risk state. | `project` |
| `scan.read` | Read scan results. | none |
| `scan.schedule.read` | Read scan schedule. | none |
| `scan.schedule.update` | Update scan schedule. | adapter/workflow dependent |
| `scan.verify.request` | Request scan verification. | adapter/workflow dependent |

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
