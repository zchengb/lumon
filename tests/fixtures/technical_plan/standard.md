---
status: "draft"
---
# Technical Plan: Persist delivery job execution metadata

## Goal & Scope

### Goal

The delivery service currently starts a scheduled notification job and emits a completion event, but it cannot distinguish a first attempt from a repeated attempt after a worker restart. Add a small execution record so the worker can claim a job once, publish a stable result, and let operators inspect the final state. The change covers the backend service and its existing event consumer; it does not change the dashboard or message wording.

### Acceptance Criteria

- **AC1 — one execution:** A scheduled job creates one execution record before work starts and the worker does not run the same job concurrently after a duplicate trigger.
- **AC2 — stable result:** A completed job stores its final state and emits one event containing the execution identifier and outcome.
- **AC3 — inspection:** An operator can query the execution status with the existing service authorization rule.
- **AC4 — unchanged delivery:** Existing notification recipients, payload content, and schedule cadence remain unchanged.

### In Scope

- `mbpass-business` job orchestration, persistence migration, execution API, and focused tests.
- `mbpass-data-proxy` event consumer contract needed to preserve the existing hand-off.

### Out of Scope

- Dashboard/UI changes, new scheduling infrastructure, recipient selection rules, and message template changes.

## Technical Decisions

### Decision 1: Claim with a unique execution key

**What is the problem?**

The scheduler can deliver the same trigger more than once when a process restarts. A timestamp alone cannot prevent two workers from entering the same job, and an in-memory flag disappears when the worker is replaced.

**Decision content**

- Derive `execution_key` from the existing job definition and scheduled occurrence, then enforce uniqueness in the execution table.
- Treat a duplicate claim as an already-known execution and return its stored state rather than starting work again.

**Decision conclusion**

**Use the persisted execution key as the idempotency boundary for job claims.**

### Decision 2: Keep the query endpoint read-only

**What is the problem?**

Operators need to inspect a job without creating a second command path that can mutate or retry delivery accidentally. The existing service already has a read authorization pattern for operational status.

**Decision content**

- Add a read-only endpoint under the existing operations resource and return the stored execution state.
- Do not expose recipient content or add a manual retry action in this Story.

**Decision conclusion**

**Expose execution metadata through the existing authorized read boundary only.**

## API & Data Design

### API / Event / Config / Command Contract

The new endpoint is backward-compatible because it adds a resource rather than changing an existing response. The caller must pass the existing operator scope. The event consumer uses the existing delivery event envelope and ignores unknown optional fields.

```json
{
  "method": "GET",
  "path": "/internal/delivery-executions/{execution_key}",
  "response": {
    "executionKey": "string",
    "jobName": "string",
    "state": "claimed | completed | failed",
    "startedAt": "timestamp",
    "finishedAt": "timestamp | null"
  }
}
```

The completion event adds `execution_key` and `state` as optional fields to the existing event payload. A repeated completion with the same key is ignored by the consumer after the first accepted result.

### Database Design

The target is based on the existing `V18__delivery_events.sql` migration, the `DeliveryEventEntity`, `DeliveryEventRepository`, and the repository's index naming convention. The event table remains unchanged; the new table stores execution state rather than recipient data.

### New table: delivery_job

**Purpose:** Store one claim and final state for each scheduled delivery occurrence.

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `execution_key` | varchar | 160 | no | — | unique index | Stable job occurrence identifier used for idempotency. |
| `job_name` | varchar | 80 | no | — | ordinary index | Existing scheduled job definition name. |
| `state` | varchar | 24 | no | `claimed` | ordinary index | Current execution state. |
| `started_at` | timestamp | — | no | current timestamp | — | Claim time. |
| `finished_at` | timestamp | — | yes | null | — | Completion time when the state is terminal. |
| `error_code` | varchar | 80 | yes | null | — | Stable failure classification without sensitive details. |

- **Application rules:** The worker accepts only the owner scope used by existing delivery jobs, and a terminal record is never silently replaced by a new result.
- **Migration note:** Add the table before deploying the worker that writes it; existing jobs have no historical execution records and remain readable through the current event path.

### Modified table: delivery_event

**Change summary**

- **Before:** Existing event rows identify the delivery message but have no execution reference.
- **After:** The event row has an optional `execution_key` used to associate a completion event with `delivery_job`.
- **Description:** The association allows inspection without changing recipient or message semantics.

**Final schema**

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `event_id` | bigint | — | no | generated | primary key | Existing event identifier; unchanged. |
| `execution_key` | varchar | 160 | yes | null | ordinary index | New optional association to `delivery_job`. |
| `payload` | json | — | no | — | — | Existing delivery payload; unchanged. |
| `created_at` | timestamp | — | no | current timestamp | — | Existing creation time; unchanged. |

## Implementation Plan

### Repository Responsibilities

- **`mbpass-business`:** owns the migration, entity/repository, job claim service, completion event fields, and read-only execution resource.
- **`mbpass-data-proxy`:** accepts the optional event fields and preserves the existing downstream delivery hand-off.

### Change Sequence

1. Add and verify the `delivery_job` migration and the optional `delivery_event.execution_key` migration using the existing migration test setup.
2. Add the entity/repository and claim service; return the stored record for duplicate execution keys.
3. Wire the scheduler and completion publisher, preserving existing recipient selection and event ordering.
4. Extend the consumer contract and add focused API, persistence, duplicate-trigger, and existing-delivery regression tests.

## Verification

- **Happy path:** trigger one scheduled occurrence, observe one claimed record, one completion event, and a terminal `completed` record.
- **Duplicate trigger:** submit the same `execution_key` twice and verify one worker execution and one stable result.
- **Failure:** force the existing delivery error path and verify a terminal `failed` state with a stable error code.
- **API/data:** query the execution resource with an authorized operator and verify persistence/read-back; reject an out-of-scope actor using the existing authorization test pattern.
- **Regression:** run migration checks, focused service tests, consumer contract tests, and the existing delivery test command.

## Risks / Open Questions

- Existing historical jobs have no execution record; the API should report not found rather than infer a state.
- If the actual migration or entity uses a different key length or timestamp type, keep the plan draft until the repository source is reconciled.
