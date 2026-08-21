---
status: "draft"
---
# Technical Plan: <Story Title>

> **Profile: Light.** Use only for one localized repository/module change with no public API change, persisted-schema migration, authorization/data-scope change, external integration, asynchronous/scheduled flow, or material deployment risk. Write in the primary language of `story.md`. Keep repository evidence in the session/tool trace, not here.
>
> Prefer bullets and short paragraphs. Do not add diagrams, database sections, API tables, performance sections, evidence inventories, or approval content unless the Story is reclassified as Standard or Complex.

## Goal & Scope

### Goal

<State the local technical outcome and the user-visible result.>

### Acceptance Criteria

- **AC1:** <observable result.>
- **AC2:** <observable result, when applicable.>

### In Scope

- <One repository/module and the behavior being changed.>

### Out of Scope (only if needed)

- <Explicit exclusion.>

## Technical Decision (only if needed)

### Decision 1: <question title>

**What is the problem?**

<The local design choice that needs to be recorded.>

**Decision content**

- <Chosen option and local boundary.>

**Decision conclusion**

**<One clear conclusion.>**

## Implementation Plan

1. **`<repository>/<file or module>`:** <concrete change and expected result.>
2. **`<repository>/<file or module>`:** <dependent local change, if any.>

Reuse the existing layer and naming convention. List only files/modules that change or are the implementation boundary; do not enumerate private methods or local variables.

## Verification

- **Happy path:** <focused scenario and supported command/manual check.>
- **Core regression:** <existing behavior that must remain unchanged and its focused check.>

## Risks / Out of Scope (only if needed)

- <Real local risk or explicit exclusion.>

<!-- The approval question is sent separately in Feishu. A PDF contains only the plan. -->
