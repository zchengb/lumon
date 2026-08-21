---
status: "draft"
---
# Technical Plan: <Story Title>

> **Profile: Standard.** This is the default profile for a general feature, one or two repositories, an API adjustment, moderate data change, one integration, or multiple modules. Write in the primary language of `story.md`; keep identifiers and repository names unchanged. Investigate repositories fully, but keep evidence in session/tool history rather than the final plan.
>
> Output order is list-first: bullets, then explanatory paragraphs, then fenced code blocks, then only necessary tables. Omit conditional sections instead of filling them with `TBD`.

## Goal & Scope

### Goal

<State the technical outcome and the user-visible result.>

### Acceptance Criteria

- **AC1 — `<short name>`:** <observable result.>
- **AC2 — `<short name>`:** <observable result.>

### In Scope

- <Repositories, modules, and behavior included.>

### Out of Scope (only if needed)

- <Explicit exclusion or frontend work blocked by policy.>

## Technical Decisions

Record only decisions that affect architecture, contracts, data, integration, permissions, failure behavior, or verification. Define each once using this structure; translate the labels to the Story language when necessary.

### Decision 1: <question title>

**What is the problem?**

<Problem and impact.>

**Decision content**

- <Chosen option and boundary.>
- <Compatibility, failure, permission, or data rule when relevant.>

**Decision conclusion**

**<One clear conclusion.>**

## API & Data Design (only when needed)

### API / Event / Config / Command Contract

Use a fenced code block for the contract. Explain caller impact, compatibility, authorization/data scope, failure behavior, and idempotency in bullets.

```text
<request / event / configuration / command contract>
```

### Database Design (only when persisted data changes)

Use the repository's actual CREATE/ALTER/rename migrations, ORM entities, repositories/mappers, and index definitions. If the target schema is unknown, keep the plan draft and record the gap; never guess.

#### New table: `<table_name>`

**Purpose:** <meaning and boundary.>

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `<field>` | `<type>` | `<length or —>` | `<yes/no>` | `<value or —>` | `<key/index or —>` | `<meaning>` |

#### Modified table: `<table_name>`

**Change summary**

- **Before:** <proven existing shape.>
- **After:** <final target shape.>
- **Description:** <reason.>

**Final schema**

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `<field>` | `<type>` | `<length or —>` | `<yes/no>` | `<value or —>` | `<key/index or —>` | `<meaning; mark changed/deleted fields>` |

- **Application rules / indexes:** <only proven rules and indexes; do not invent database foreign keys.>

## Implementation Plan

### Repository Responsibilities

- **`<repository>`:** <role, module/layer, and why it changes.>
- **`<repository>`:** <role, or omit when not applicable.>

### Change Sequence

1. <Concrete file/module boundary and prerequisite change.>
2. <API, event, persistence, configuration, or integration wiring.>
3. <Failure, retry, permission, identity, or idempotency handling when applicable.>
4. <Focused documentation/operational hand-off only when required.>

Name public or cross-module contracts and changed files. Do not produce a full private identifier inventory.

## Verification

- **Happy path:** <scenario and repository-supported command/manual check.>
- **Boundary and failure:** <invalid, empty, duplicate, permission, timeout, or no-change scenario when relevant.>
- **API/data/integration:** <contract, persistence/read-back, or integration check when applicable.>
- **Regression:** <existing behavior and focused regression command.>

## Risks / Open Questions (only when real)

- <Destructive, one-way, incompatible, security, dependency, or unresolved design risk.>
- <Question that must be answered before approval.>

<!-- Approval is a separate Feishu conversation. Never place Technical Plan Approval in this document or its PDF. -->
