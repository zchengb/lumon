<!-- Lumen managed: agent-skill -->

# Technical Loop workflow

This loop starts only after the Story/Business Loop has produced `story.md` with `metadata.json.businessStatus=ready`. If that prerequisite is absent, return to Business Loop, keep the explanation in Feishu text, and do not draft a Technical Plan or generate its PDF.

The Feishu Loop Gateway is an accepted entry point. A clear request to turn one business-ready Story into a technical plan starts this workflow directly; an ambiguous request gets one concise confirmation. The gateway never authorizes delivery or application-code changes.

Frontend delivery is disabled. Do not plan or approve Web, Native, mobile UI, frontend source, Figma-to-code, browser/device runtime, Visual Delivery Contract, or visual QA work. Keep it out of scope or blocked; backend-only work may proceed only when independently deliverable without frontend changes.

## Preflight and Investigation

Refresh the docs repository and relevant clean code repositories safely. For a Story with `metadata.json.jiraKey`, invoke `$lumen-jira-story-import` before reading requirements. If `jiraSyncStatus` is `changed`, ask exactly:

```text
Jira changed since this Story was confirmed. A. Pull and reconcile the Jira changes in the Business Loop B. Keep the local Story and continue technical planning C. Review the difference first
```

Only A returns to Business Loop. B is an explicit local-source decision. Inspect real modules, migrations, ORM entities, repositories/mappers, indexes, APIs/events, tests, architecture guards, runtime/config, permissions, and integrations before making a plan. Never modify application source code.

## Profile and Template

Recommend the smallest sufficient profile and explain why; the user may override it:

- **Light:** read `templates/technical-plan-light.md` for one localized repository/module change with no public API, schema migration, permission/data scope, integration, async/scheduled flow, or material deployment risk.
- **Standard:** read `templates/technical-plan-standard.md` for normal moderate work. `templates/technical-plan.md` is the compatibility/default Standard entry point.
- **Complex:** read `templates/technical-plan-complex.md` for multi-repository/service, migration/rename, public or cross-service contract, integration, permission/data scope, async/state, or major placement work.

The profile changes output density, not correctness. Light stays concise; Standard adds only the API/data/architecture details it needs; Complex records the additional cross-boundary decisions and verification. Do not add sections merely because a profile is Complex.

All plans use the Story's primary language, list-first prose, fenced code blocks for API/event/config/command/payload contracts, and tables only for inherently two-dimensional data. Omit empty conditional sections. Repository evidence is required for investigation but stays in tool/session trace, git, or Jira context rather than the final plan. Do not add a mandatory class diagram, full private identifier inventory, performance matrix, release-order block, deployment recovery block, or approval block.

## Decisions, Data, and Verification

For each confirmed decision, use one block and define it once:

```markdown
### Decision N: <question title>
**What is the problem?**
<problem and impact>
**Decision content**
- <chosen option and boundary>
**Decision conclusion**
**<one clear conclusion>**
```

For a new or modified table, ground the final field-level schema in actual migrations, ORM entities, repositories/mappers, and indexes. Include field, type, length/precision, null, default, key/index, and explanation. Unknown schema facts remain a draft gap; never guess. Use application-level relationship validation and existing index conventions rather than inventing database foreign keys.

Keep only design-significant identifiers: public API/event fields, persisted fields, cross-service DTOs, config/definition keys, confusing domain names, and public/shared methods when the name itself is a decision. Do not list every private method or local variable.

Verification is list-first and profile-appropriate: Light covers happy path and core regression; Standard adds material boundary/API/data/integration checks; Complex adds cross-repository contract, migration, async/state/idempotency, and permission/identity checks when applicable. Name actual supported commands or scenarios and expected results.

Use the Lumen Grill protocol for unresolved decisions: ask one question at a time when answers depend on each other, otherwise batch up to four independent questions. Each question has 2–4 options, a recommended option when justified, the impact, and a custom-answer path. Do not ask what repository evidence already resolves.

## Business Boundary and Approval

If evidence reveals a business ambiguity affecting ACs, rules, actors/roles, data visibility, scope, failure behavior, or promised timing, keep `technicalStatus=draft`, show options, and return to Business Loop. Do not alter `story.md` here.

Before approval, complete investigation, profile, decisions, contracts, concrete verification, and real risks/open questions with no blocking `TBD`. Save only the Technical Plan. The following is Feishu conversation text, not Markdown content, and must not be appended to the plan or PDF:

```text
A. Approve this Technical Plan
B. Continue refining
C. Keep it as draft
D. Request a Business Loop revision
```

Only explicit A may set `metadata.json.technicalStatus` to `approved`. A substantive approved-plan change returns it to `draft`; formatting-only changes do not. A PDF export must contain the plan only.
