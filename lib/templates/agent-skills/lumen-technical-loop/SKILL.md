---
name: lumen-technical-loop
description: Use when the user explicitly asks for a Technical Loop or when the Feishu Loop Gateway detects a clear request to turn one business-ready Lumen Story or requirement into a technical plan/design. For a combined Story Plan + Technical Plan request, enter only after the Business/Story stage is ready. It may modify that Story's technical-plan.md and metadata.json; it must not modify application source code or story.md.
---

<!-- Lumen managed: agent-skill -->

# Lumen Technical Loop

Read `references/workflow.md` and `standards/technical-loop.md` before acting. Use the smallest sufficient profile and keep status in `metadata.json`; do not use a CLI approval command. Frontend/Web/Native UI delivery, Figma-to-code, browser/device runtime, Visual Delivery Contracts, and visual QA are disabled.

Technical Loop requires `metadata.json.businessStatus=ready`. If the Story is not business-ready, stop before drafting or presenting `technical-plan.md`, explain the prerequisite in Feishu text, and return to Business Loop. The loop may run in Codex, Cursor, or another compatible Agent, but it is planning-only and never modifies application source code or `story.md`.

## Profile Selection

After repository investigation, recommend one profile and let the user override it:

- **Light:** `templates/technical-plan-light.md`; one localized repository/module change with no public API, schema migration, permission/data scope, integration, async/scheduled flow, or material deployment risk.
- **Standard:** `templates/technical-plan-standard.md`; normal moderate work. `templates/technical-plan.md` is the compatibility/default Standard template.
- **Complex:** `templates/technical-plan-complex.md`; multi-repository/service, migration/rename, public/cross-service contract, integration, permission/data scope, async/state, or major placement work.

The selected template controls density. Do not inherit Complex-only sections into Light or Standard. Write in the primary language of `story.md`; use bullets first, fenced code blocks for machine-readable contracts, necessary tables only for 2D data, and omit conditional sections rather than filling them with boilerplate.

## Required Planning Behavior

1. Inspect actual repositories, migrations, ORM entities, repositories/mappers, indexes, APIs/events, tests, architecture guards, runtime/config, permissions, and integrations before drafting.
2. Keep detailed Repository Evidence in tool/session trace, git, or Jira context. Record only the decision, contract, implementation boundary, verification, and real risk in `technical-plan.md`.
3. Ask unresolved technical questions with the Lumen Grill protocol: sequentially when dependent, otherwise in a small batch; provide 2–4 options, impact, a justified recommendation, and a custom-answer path.
4. Record every confirmed decision once using `What is the problem?`, `Decision content`, and one bold `Decision conclusion`; do not use a default decision table or duplicate rationale.
5. Put API, event, configuration, command, and payload contracts in fenced code blocks. Ground new/modified table schemas in actual migrations/entities/repositories/indexes; unknown facts remain draft and must not be guessed.
6. Keep only design-significant identifiers: public/shared contracts, persisted fields, cross-service DTOs, config keys, confusing domain names, and methods whose names are themselves decisions. Do not list every private method or local variable.
7. Use profile-appropriate list-first verification with actual commands/scenarios. Do not add a mandatory class diagram, evidence dump, performance matrix, release-order section, deployment recovery section, or approval block.
8. Save only the plan in `technical-plan.md`. Send the approval question as ordinary Feishu text; an exported PDF contains the plan only.
9. Ask for explicit approval before setting `technicalStatus` to `approved`. A substantive approved-plan change returns it to `draft`.

## Status

Valid `businessStatus` values are `draft`, `clarifying`, `ready`, `blocked`, and `changed`.

Valid `technicalStatus` values are:

- `draft` — planning, questioning, refinement, or review is still in progress.
- `approved` — the user explicitly approved; Development Loop may start.

Do not start Development Loop until both `businessStatus=ready` and `technicalStatus=approved`. Code implementation runs through `lumen delivery run` and follows the approved plan.

## Feishu Approval Prompt

Never write `## Approval`, `## Technical Plan Approval`, or answer choices into `technical-plan.md` or its PDF. After saving the plan, send exactly:

```text
A. Approve this Technical Plan
B. Continue refining
C. Keep it as draft
D. Request a Business Loop revision
```

## Agent Response Format

Every conversational response should make these items clear without copying them into the plan unless they are actual plan content:

### Evidence

Files or repository facts used; keep detailed excerpts in the trace.

### Clarifications

Questions asked and confirmed answers.

### Changes Made

Plan or metadata files changed.

### Risks

Remaining ambiguity or risk.

### Next Step

Recommended action or the separate approval prompt.
