---
status: "draft"
---
# Technical Plan: <Story Title>

> **Default profile: Standard.** Write this document in the primary language of `story.md`; keep repository names, code identifiers, API names, and Jira keys unchanged. Repository investigation remains mandatory, but its evidence belongs in the session/tool trace, not in this document.
>
> Keep the output list-first: bullets before paragraphs, code blocks before tables, and tables only for inherently two-dimensional data. Omit a conditional section instead of leaving an empty placeholder.

## Goal & Scope

### Goal

<State the technical outcome and the user-visible result in one or two sentences.>

### Acceptance Criteria

- **AC1 — `<short name>`:** <observable technical outcome and user-visible result.>
- **AC2 — `<short name>`:** <observable technical outcome and user-visible result.>

### In Scope

- <Repository/module/behavior included in this Story.>

### Out of Scope (only if needed)

- <Only include explicit exclusions or frontend work blocked by policy.>

## Technical Decisions

Include this section only when a design choice needs owner confirmation. Define each decision once. Use the following four-part format, translating the labels to the Story language when necessary:

### Decision 1: <question title>

**What is the problem?**

<Describe the unresolved technical problem and its impact.>

**Decision content**

- <Chosen option and the boundary it establishes.>
- <Compatibility, failure, permission, or data rule when relevant.>

**Decision conclusion**

**<One clear conclusion.>**

## API & Data Design (only when applicable)

### API / Event / Config / Command Contract

Put machine-readable contracts in fenced code blocks. Explain compatibility, authentication/data scope, failure behavior, and idempotency in bullets immediately around the block.

```json
{
  "name": "<endpoint, event, config key, or command>",
  "request": "<shape>",
  "response": "<shape>"
}
```

### Database Design (only when persisted data changes)

Ground the design in the repository's actual migrations, ORM entities, repositories/mappers, and index definitions. If the final schema cannot be proven, keep `technicalStatus` as `draft` and record the open gap instead of guessing.

#### New table: `<table_name>`

**Purpose:** <why this table exists and what it must not represent.>

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `<field>` | `<type>` | `<length or —>` | `<yes/no>` | `<value or —>` | `<key/index or —>` | `<meaning>` |

- **Indexes:** <only indexes supported by repository evidence.>
- **Rules / relationship:** <application-level validation and relationship rules; do not invent database foreign keys.>
- **Migration note:** <ordering or data treatment when relevant.>

#### Modified table: `<table_name>`

**Change summary**

- **Before:** <existing proven schema or field name.>
- **After:** <final schema and field name.>
- **Description:** <why the change is required.>

**Final schema**

| Field | Type | Length / precision | Null | Default | Key / index | Explanation |
|---|---|---|---|---|---|---|
| `<field>` | `<type>` | `<length or —>` | `<yes/no>` | `<value or —>` | `<key/index or —>` | `<meaning; mark changed/deleted fields>` |

## Implementation Plan

### Repository Responsibilities

- **`<repository>`:** <the responsibility and why this repository is touched.>
- **`<repository>`:** <the responsibility, or omit when there is only one repository.>

### Change Sequence

1. <Concrete module/file boundary and the change it makes.>
2. <Dependent API, event, persistence, configuration, or integration wiring.>
3. <Failure, retry, permission, identity, or idempotency behavior when applicable.>
4. <Documentation or operational hand-off only when required by the Story.>

Name the relevant file/module and public contract when it is a design boundary. Do not inventory private methods, local variables, or unchanged files.

## Verification

- **Happy path:** <focused scenario and the repository-supported command or manual check.>
- **Boundary/failure:** <invalid, empty, duplicate, permission, timeout, or no-change case when relevant.>
- **API/data/integration:** <contract, persistence/read-back, or integration check when applicable.>
- **Regression:** <existing behavior and the focused test command that protects it.>

Use only verification capabilities that the affected repository actually provides. Do not create a verification matrix for a plan that can be expressed as a short list.

## Risks / Open Questions (only when real)

- <Destructive, one-way, incompatible, security, dependency, or unresolved design risk.>
- <Owner question that must be answered before approval.>

<!--
Profile boundary:
- Light uses the smaller Light template and must not inherit sections from this Standard template.
- Standard includes only the API/data/diagram details required by this Story.
- Complex uses the Complex template for multi-repository, migration, permission/data-scope, public API, integration, async, state-flow, or major placement work.
The approval prompt is Feishu conversation text, never plan content. A PDF export contains only this plan.
-->
