# Technical Loop

The Technical Loop turns one concrete, business-ready `story.md` into one executable `technical-plan.md`. It may run in Codex, Cursor, or another compatible Agent, but it remains planning-only: it may change the delivery document and metadata status, never application source code or `story.md`.

## Frontend Delivery Policy

Frontend delivery is disabled. Do not plan or approve Web, Native, mobile UI, frontend source, Figma-to-code, browser/device runtime, Visual Delivery Contract, or visual QA work. Keep that portion out of scope or blocked and return to the Business Loop when the Story cannot be delivered without it. Backend-only work may proceed only when it is independently deliverable without frontend changes.

## Inputs

- `story.md`
- `metadata.json`
- Existing `technical-plan.md` when refining a draft
- `lumen/context/<story>/jira-context.json` when the Story is linked to Jira
- Relevant repository context under `repos/<repository>/`
- `standards/business-loop.md`
- The profile template selected below
- Runtime profile, Dockerfile, or stack information when available

## Outputs

- Updated `technical-plan.md` in the Story's primary language
- `metadata.json.technicalStatus` kept as `draft` until explicit approval
- Updated `metadata.json.linkedRepos` only when confirmed repository scope changes
- A clear text explanation of any blocker or unresolved question

Detailed repository evidence belongs in session/tool history, trace, git, or Jira context. The final Technical Plan records the decision or contract that evidence supports, not a copied evidence report.

## Preflight Sync

Use the same safe preflight rules as the Business Loop:

1. Pull this docs repository first.
2. Pull each configured code repository under `repos/` that may be used as context.
3. Check `git status` before pulling each repository.
4. Run `git pull --ff-only` only when the repository has no local uncommitted changes.
5. If a repository cannot be refreshed safely, stop and ask how to proceed.

For a Story with `metadata.json.jiraKey`, invoke `$lumen-jira-story-import` before reading requirements. If `jiraSyncStatus` is `changed`, ask the required Business Loop reconciliation question. Only an accepted reconciliation changes `story.md`; never overwrite local Story edits silently.

## Gates

Do not start until:

- The input is one concrete Story, not a broad topic.
- `metadata.json.businessStatus` is `ready`.
- `story.md` has clear Acceptance Criteria and no blocking business `TBD`.

Keep `technicalStatus` as `draft` while investigating, asking, drafting, or refining. Do not start the Development Loop until the plan exists and `technicalStatus` is explicitly `approved`.

## Profile Selection and Output Contract

Recommend the smallest sufficient profile after repository investigation and let the user override it. Use the matching template:

- **Light:** `templates/technical-plan-light.md`. One repository/module and local logic only; no public API, persisted-schema migration, authorization/data-scope change, external integration, async/scheduled flow, or material deployment risk. Suggested output is 300–700 words.
- **Standard:** `templates/technical-plan-standard.md`; `templates/technical-plan.md` remains the compatibility/default entry point with the same Standard structure. Use for a general feature, one or two repositories, API adjustment, moderate data change, one integration, or multiple modules. Suggested output is 700–1500 words.
- **Complex:** `templates/technical-plan-complex.md`. Use for multi-repository/service work, migrations or renames, permissions/data scope, public or cross-service contracts, integrations, async/scheduled flows, state transitions, or major placement decisions. Suggested output is 1200–2500 words.

All profiles follow these rules:

- Write in the primary language of `story.md`; preserve code identifiers, repository names, API names, and Jira keys.
- Use the order: bullets, short paragraphs, fenced code blocks, then tables only where the data is inherently two-dimensional.
- Omit conditional sections instead of leaving empty headings, `TBD`, or boilerplate.
- Do not put Repository Evidence, an evidence dump, a full private identifier inventory, an approval block, a release-order block, or a deployment recovery plan in the final Technical Plan.
- A diagram is conditional. Standard may use one flow diagram when a cross-module/service, scheduled, async, state, or filtering flow needs it. Complex may use zero or one main end-to-end diagram; add a class/component diagram only when that relationship is itself the design problem. Light normally has no diagram.
- Complexity increases the number of real decisions and boundaries, not the number of headings.

## Flow

1. Read `story.md`, `metadata.json`, the selected profile template, and the coding guideline shipped with the CLI.
2. Inspect actual repositories before drafting: module/layer boundaries, endpoints, jobs, migrations, ORM entities, repositories/mappers, indexes, tests, architecture guards, Dockerfiles, runtime/config, permissions, and recent patterns.
3. Build an impact map: repositories, modules, APIs/events, persisted data, configuration, permissions, integrations, async/state, and verification surfaces.
4. Recommend the profile and explain the boundary. If the work does not fit Light, do not force it into the Light template.
5. Use the Lumen Grill protocol for unresolved technical decisions. Ask sequentially when one answer depends on another; otherwise batch up to four independent questions. Offer 2–4 options, mark a recommended option when supported, explain impact, and allow a custom answer.
6. Record confirmed technical decisions in `technical-plan.md`; do not repeat one decision in several sections.
7. Draft only the sections required by the selected profile. Keep the plan implementation-ready without inventing architecture or schema.
8. Save only the plan in `technical-plan.md`. Send approval choices separately as Feishu text; a PDF export contains the plan only.
9. Ask for explicit approval before setting `technicalStatus` to `approved`.
10. Never modify application source code in this loop.

## Technical Decision Contract

For each design decision, use one block with four parts. Translate the labels to the Story language while preserving their meaning:

```markdown
### Decision N: <question title>

**What is the problem?**
<problem and impact>

**Decision content**
- <chosen option and boundary>

**Decision conclusion**
**<one clear conclusion>**
```

Do not use a default `Decision | Rationale | Boundary` table. Do not scatter the same rationale across decisions, API sections, and implementation steps. If a decision changes business behavior, return to Business Loop rather than editing `story.md` here.

## Contracts and Schema Rules

- API, event, configuration, command, and payload contracts use fenced code blocks. Explain compatibility, authentication/data scope, failure, retry, and idempotency in nearby bullets.
- A new table gets its own subsection with purpose and a field-level table containing: field, type, length/precision, null, default, key/index, and explanation, followed only by applicable indexes, rules, relationship, and migration notes.
- A modified table gets a Before/After/Description change summary and a final-schema field table with the same columns. Use final names after a rename and mark deleted fields.
- Ground every schema claim in actual CREATE/ALTER/rename migrations, ORM entities, repositories/mappers, and index definitions. If a final schema fact is unknown and can change the design, keep `technicalStatus=draft` and record the gap; never guess.
- Do not plan database foreign keys; use existing application-level relationship validation and ordinary indexes unless repository standards explicitly require otherwise.
- Keep only design-significant identifiers: public API/event fields, persisted fields, cross-service DTOs, configuration/definition keys, confusing domain names, and public/shared methods when the name itself is a decision. Do not list every private method or local variable.

## Verification Rules

Verification is list-first and profile-appropriate:

- **Light:** happy path, core regression, and a focused command/manual check supported by the repository.
- **Standard:** happy path, material boundaries, API/data/integration checks when applicable, and existing regression.
- **Complex:** cross-repository contract, persistence/migration, async/state/idempotency, permission/identity, and existing regression checks when applicable.

Name the real command or manual scenario and the expected result. Do not create a mandatory Verification Matrix. Assess a query, batch, API, integration, or async flow only to the extent needed to make its bounds, failure behavior, and verification concrete; do not add a generic performance section when it does not affect the design.

## Business Ambiguity and Frontend

If repository facts expose an ambiguity affecting Acceptance Criteria, business rules, actors/roles, permission/data visibility, scope, failure behavior, or promised freshness/timing/availability, keep the plan draft, show the options, and return to Business Loop. Do not modify `story.md` from Technical Loop.

If the Story requires UI, frontend, Figma-to-code, browser/device, or visual delivery work, record that scope as blocked/out of scope. Do not call Figma tools, create a Visual Delivery Contract, or approve a plan that depends on frontend changes.

## Plan Quality Bar

Keep the plan draft and refine it when:

- A required decision has no clear conclusion or the same decision is repeated.
- An API/event contract is needed but missing or not represented as a code block.
- A persisted schema is needed but the target table/field/index details are unknown or guessed.
- A repository is listed without its role and concrete module/file boundary.
- Async, idempotency, permission/identity, or cross-service compatibility matters but is not addressed.
- Verification names only “run tests” without an actual supported command or scenario.
- The plan contains empty boilerplate, an evidence dump, a mandatory diagram/class inventory, or an approval block.

Deployment sequencing and recovery belong to delivery operations when required; they are not mandatory Technical Plan sections. Risks may still call out destructive, one-way, incompatible, security, or operational consequences.

## Approval (Feishu conversation only)

Never write `## Approval`, `## Technical Plan Approval`, status explanations, or answer choices into `technical-plan.md`. Save only the plan, then ask:

```text
A. Approve this Technical Plan
B. Continue refining
C. Keep it as draft
D. Request a Business Loop revision
```

Only explicit A may set `metadata.json.technicalStatus` to `approved`. A substantive change after approval returns it to `draft`; formatting-only changes do not.

## Status and Language

Valid `technicalStatus` values are `draft` and `approved`. If the Story changes after approval, set it back to `draft` and revise the plan. Write `technical-plan.md` in the same primary language as `story.md` unless the user asks otherwise.
