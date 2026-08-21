---
status: "draft"
---
# Technical Plan: <Story Title>

> **Profile: Complex.** Use when the Story genuinely needs multiple repositories/services, a persisted-schema migration or rename, permissions/data scope, a public or cross-service contract, external integration, asynchronous/scheduled work, state transitions, or a major architecture-placement decision. Complexity means more core decisions and coordination, not more boilerplate. Write in the primary language of `story.md`.
>
> Repository investigation is mandatory. Store detailed evidence in session/tool history, trace, git, or Jira context; the final plan contains the resulting decisions, contracts, boundaries, verification, and real risks only.

## Goal & Scope

### Goal

<State the technical outcome and user-visible result.>

### Acceptance Criteria

- **AC1 — `<short name>`:** <observable result.>
- **AC2 — `<short name>`:** <observable result.>

### In Scope

- <Repositories/services, actors, data, and behavior included.>

### Out of Scope (only if needed)

- <Explicit exclusion, including frontend work blocked by policy.>

## Technical Decisions

Record the small set of decisions that determine architecture, contracts, data, permissions, async behavior, or sequencing. Define every decision once and translate the labels to the Story language when necessary.

### Decision 1: <question title>

**What is the problem?**

<Problem, evidence-backed impact, and the boundary of the choice.>

**Decision content**

- <Chosen option.>
- <Compatibility, failure, permission, identity, or data rule.>

**Decision conclusion**

**<One clear conclusion.>**

### Decision 2: <question title>

**What is the problem?**

<Problem and impact.>

**Decision content**

- <Chosen option and boundary.>

**Decision conclusion**

**<One clear conclusion.>**

## Architecture (usually one main diagram)

Describe service/repository ownership, module placement, hand-offs, state transitions, and failure boundaries. Add **zero or one** main Mermaid end-to-end diagram only when it makes the cross-system or asynchronous behavior easier to verify. Add a component/class diagram only when the class/component relationship itself is the design problem; it is not a default section.

<!-- Put one real Mermaid flowchart here only when the architecture is unclear without it. -->

### Repository / Service Responsibilities

- **`<repository or service>`:** <owned boundary, entry point, and reason for change.>
- **`<repository or service>`:** <owned boundary and hand-off.>

### Runtime, Permission, and Integration Boundaries (only when applicable)

- **Runtime/config:** <actual profile, Dockerfile, secret/config key, and environment boundary.>
- **Permission/identity:** <actor, scope, authorization point, and audit expectation.>
- **Async/state:** <trigger, consumer/job, state transitions, retry, duplicate handling, and idempotency key.>
- **Integration:** <upstream/downstream contract, timeout, failure signal, and observability.>

## API & Data Design

### API / Event / Config / Command Contract (when applicable)

Use fenced code blocks for machine-readable contracts. State compatibility, caller impact, authentication/data scope, failure behavior, retry, and idempotency in bullets.

```json
{
  "name": "<endpoint, event, config key, or command>",
  "request": "<shape>",
  "response": "<shape>",
  "errors": ["<stable error>"]
}
```

### Database Design (when persisted data changes)

The target must be grounded in actual CREATE/ALTER/rename migrations, ORM entities, repositories/mappers, and index definitions. If any final type, nullability, default, key, index, rename, or delete is unknown, keep `technicalStatus` as `draft` and record the open gap; do not guess.

#### New table: `<table_name>`

**Purpose:** <what the table represents and what it explicitly does not represent.>

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `<field>` | `<type>` | `<length or —>` | `<yes/no>` | `<value or —>` | `<key/index or —>` | `<meaning>` |

- **Indexes:** <proven index definitions and query purpose.>
- **Application relationship rules:** <validation and ownership rules; do not add database foreign keys.>
- **Migration/data treatment:** <dependency order, rename, backfill, or compatibility window when applicable.>

#### Modified table: `<table_name>`

**Change summary**

- **Before:** <proven current schema.>
- **After:** <final target schema with final names.>
- **Description:** <reason and compatibility boundary.>

**Final schema**

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `<field>` | `<type>` | `<length or —>` | `<yes/no>` | `<value or —>` | `<key/index or —>` | `<meaning; mark changed/deleted fields>` |

## Implementation Plan

### Dependency-ordered Changes

1. **`<repository>/<file or module>`:** <migration/model/config prerequisite and expected result.>
2. **`<repository>/<file or module>`:** <service/API/event implementation and contract.>
3. **`<repository>/<file or module>`:** <consumer/job/integration wiring, retry, and idempotency.>
4. **`<repository>/<file or module>`:** <permission, observability, and focused tests.>

For each repository, name its role and concrete change boundary. List public APIs, persisted fields, cross-service DTOs, configuration keys, and other design-significant identifiers only when they are changed or semantically confusing; do not enumerate every private method or local variable.

## Verification

- **Cross-repository contract:** <compatible request/event/DTO behavior and the supported command or integration check.>
- **Persistence/migration:** <new/changed schema, read-back, rename, empty-data, and data-integrity scenarios.>
- **Async/state/idempotency:** <trigger, retry, duplicate, timeout, and state-transition scenarios when applicable.>
- **Permission/identity:** <actor and data-scope allow/deny scenarios when applicable.>
- **Existing regression:** <actual focused unit/integration/static/architecture checks available in each repository.>

## Risks / Open Questions (only when real)

- <Destructive, one-way, incompatible, security, dependency, or operational risk.>
- <Unresolved schema, contract, scale, or ownership question that blocks approval.>

<!--
Do not add a mandatory class diagram, performance matrix, release-order section, evidence dump, or approval block. Deployment recovery and release sequencing belong to delivery operations when they are needed, not to the Technical Plan output contract.
The approval prompt is sent separately in Feishu. A PDF export contains only this plan.
-->
