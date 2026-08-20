# Technical Loop

The Technical Loop turns one concrete, business-ready `story.md` into one executable `technical-plan.md`. It may run in Codex, Cursor, or another Agent, but it must stay in planning mode: no application source code changes are allowed in this loop.

## Frontend Delivery Policy

Frontend delivery is disabled (Does not include manual execution). The Technical Loop must not approve a plan whose delivery includes Web, Native, mobile UI, frontend source changes, Figma-to-code work, a Visual Delivery Contract, browser/device runtime work, or visual QA. Keep that portion out of scope and return to the Business Loop when the Story cannot be delivered without it. Backend-only work may proceed only when it is independently deliverable without frontend changes.

## Inputs

- `story.md`
- `metadata.json`
- Existing `technical-plan.md` when refining a previous draft
- `lumen/context/<story>/jira-context.json` when the Story is linked to JIRA
- Relevant repository context from `repos/<repository>/`
- `standards/business-loop.md`
- `templates/technical-plan.md`
- Runtime profile, Dockerfile, or stack information when available

## Outputs

- Updated `technical-plan.md`
- Updated `metadata.json.technicalStatus` through Lumen or explicit status update
- Updated `metadata.json.linkedRepos` when repository scope changes
- Clear list of remaining blockers when the plan cannot be approved

## Preflight Sync

Use the same preflight rules as the Business Loop:

1. Pull this docs repository first.
2. Pull every configured code repository under `repos/` that may be used as context.
3. For each repo, check `git status` before pulling.
4. Run `git pull --ff-only` only when the repo has no local uncommitted changes.
5. If a repo cannot be fast-forwarded safely, stop and ask the user how to proceed.

## Gate

Do not start the Technical Loop until:

- The input is a single concrete story, not a broad topic.
- `metadata.json.businessStatus` is `ready`.
- `story.md` has clear Acceptance Criteria and no important `TBD`.

If the user starts from a topic, guide them to split and select one story first. Generate technical plans story by story, never one technical plan for an entire topic.

Do not start the Development Loop until:

- `technical-plan.md` exists
- `metadata.json.technicalStatus` is `approved`

## Flow

1. Read `story.md`, `metadata.json`, `templates/technical-plan.md`, and this standard.
2. Inspect the real repositories before drafting: architecture and package boundaries, modules, endpoints, jobs, tables, tests, architecture guard tests, Dockerfile, build files, permission conventions, and recent patterns.
3. Keep `technicalStatus` as `draft` while planning or asking questions. Recommend Light, Standard, or Complex after investigation, explain why, and let the user override. Light is a localized one-repository change without API, schema, authorization/data-scope, integration, async/scheduled, or material rollback impact; Standard is normal moderate work; Complex covers multi-repo, migration, permission/data scope, public/cross-service API, integration, async/state flow, high rollback risk, or major placement decisions. Use the smallest sufficient profile and never fill irrelevant sections.
4. Build an initial impact map: repositories, modules, API/data/config/permission/test surfaces.
5. Build a domain-concept map before choosing a class, table, API, method, or variable name. Compare every Story term with existing domain objects, APIs, database fields, and recent refactors. Explicitly distinguish the same concept with a new label, a specialization, and a genuinely new concept.
6. Ask derived technical questions progressively when an answer affects concept mapping, design, delivery boundary, verification, or rollout. When an ambiguous business term may map to an existing model, ask and confirm this before drafting class-level changes.
7. Record every confirmed answer in `technical-plan.md`; do not leave decisions only in chat.
8. Derive a concise DC Checklist from the confirmed Acceptance Criteria, Business Rules, JIRA context, and repository behavior. It is the BA/QA/Developer walkthrough for confirming that the delivered Story works end to end.
9. For a non-trivial behavior, data, or multi-class change, add both a business flow diagram and an implementation interaction/class diagram. Name the existing and proposed classes, entry methods, and hand-off points that the Delivery Agent must use.
10. Publish a naming contract for changed/new public methods, persisted fields, API fields, DTO properties, and key local variables whose semantics can be confused with an existing concept.
11. Produce a file-level implementation plan detailed enough for another engineer or Agent to implement without guessing.
12. Add concise Repository Evidence for important decisions: decision, repository path and symbol, and what it proves. Paste only a 3-8 line excerpt when a path and symbol are insufficient.
13. If the Story requires a UI, frontend, Figma-to-code, browser/device, or visual-delivery change, keep that delivery scope out of the Technical Loop and record it as out of scope or blocked. Do not call Figma MCP or create a Visual Delivery Contract for it.
14. If inspection reveals a business ambiguity affecting ACs, rules, user-visible behavior, actor/role, permission/data visibility, scope, failure behavior, or promised freshness/timing/availability, keep draft, show evidence and options, and return to Business Loop; do not modify `story.md` from this loop.
15. Before approval, confirm investigation, profile, questions, concrete verification, and Plan Quality Bar are complete with no blocking TBD. Present profile/reason, repositories, approach, important decisions, applicable impacts, verification, risks, and Out of Scope. Ask: `A. Approve this Technical Plan`, `B. Continue refining`, `C. Keep it as draft`, or `D. Request a Business Loop revision`.
16. Only explicit A may set `technicalStatus` to `approved`. A substantive later change returns it to draft and requires approval again; formatting-only changes do not.

## Progressive Technical Q&A

Use interactive Q&A whenever the environment supports it.

Rules:

- Use the Lumen Grill protocol for remaining high-impact technical questions. Ask one question at a time when the next answer depends on the previous answer; otherwise use a small checklist batch when the user asks for a plan.
- Ask the questions that most affect architecture, data model, API contract, runtime, or verification first, and skip anything repository evidence already resolves.
- Provide 2-4 concrete options per question and mark one as `Recommended` when reasonable.
- Always allow a custom answer.
- Prefer choices over blanks. Do not ask the user to fill an empty template field when you can offer likely options from repo context.
- Explain the consequence of each option briefly.
- Record the final answers in `technical-plan.md` under `Technical Clarifications` or the relevant plan section.
- Return to the Business Loop if an answer changes business scope or Acceptance Criteria.

Example:

```text
Please answer all of the following in one reply.
For each question, choose a letter or type your own answer.

1. Question: Where should the low-rating aggregation job be implemented?
A. Existing scheduled-job module in mbpass-business (Recommended) - keeps survey aggregation close to existing domain logic.
B. New admin-side scheduled task - faster UI-team ownership, but duplicates business-domain access.
C. External script / operations job - lowest code change, but weak observability and deployment control.
D. Other: describe your answer.

2. Question: How should empty survey batches be handled?
A. No-op with structured log (Recommended)
B. Create an empty result row
C. Fail the job
D. Other: describe your answer.
```

## Required Technical Question Areas

The Agent should actively check these areas and ask only when the answer is not clear from docs or code:

- Repository scope: which repos must change, and which repos are explicitly read-only for this story.
- Domain concept mapping: whether each business term is identical to, a specialization of, or distinct from an existing domain concept. Ask this before proposing new tables, classes, enums, fields, or parallel flows. Give the user concrete alternatives from repository evidence.
- Base branch and worktree boundary: target branch, feature branch naming, and whether multi-repo PRs are needed.
- Architecture placement: controller/service/repository/job/component ownership and existing module conventions.
- Code conventions and architecture guards: existing naming, error/logging/transaction patterns and any ArchUnit, package-boundary, PMD, Checkstyle, ESLint, or equivalent guard. The plan must preserve them; it must not invent a parallel structure.
- API contract: endpoint, request/response, authorization, compatibility, and caller impact.
- Data model: tables, migrations, indexes, default values, backfill, rollback, and data retention. Do not plan database foreign keys; use application-level relationship validation and ordinary indexes where needed.
- Integration boundary: upstream/downstream services, queues, scheduled jobs, email/SMS/push providers, and failure handling.
- Runtime and environment: Java version, project-provided Dockerfile, runtime profile, secrets, config keys, and local limitations.
- Visual/UI design: frontend and visual delivery are disabled. Do not plan UI implementation, Figma-to-code, browser/device QA, or Visual Delivery Contract work; keep it out of scope or blocked.
- Verification: identify the repository's actual test capability first. For Java, plan compile/static analysis, focused unit tests, integration tests, and architecture guards when those patterns exist. For App/PHP repos, plan only syntax/type/lint and explicitly permitted focused tests; do not assume heavy environment-dependent builds.
- Permission and data scope: identify affected actors, roles/permissions, ownership, tenant/dealer scope, audit expectations, and the matching authorization test pattern.
- Observability: logs, metrics, audit trail, alerting, and support diagnostics.
- Rollout and rollback: feature flags, config switch, release sequencing, and rollback plan.
- Refactoring boundary: local cleanup allowed inside the story vs separate refactor discussion.
- Out of scope: what the Development Loop must not implement.

## Required Plan Detail

`technical-plan.md` must be implementation-ready. At minimum include:

- Goal and delivery scope tied to Acceptance Criteria
- DC Checklist derived from Acceptance Criteria, Business Rules, JIRA context, and repository behavior
- Domain Concept And Naming Contract: business term -> existing model or new model -> canonical API/table/class/property/method names -> explicitly forbidden duplicate concepts or names
- Business flow diagram and implementation interaction/class diagram for every non-trivial behavior, data-model, or multi-class change
- Technical clarifications with confirmed answers
- Impacted repositories and why each is touched
- Architecture summary and layer placement
- File-level change list per repository
- Public and behavior-significant method/variable/property naming contract, including the semantic reason for each name
- API, schema, migration, config, permission, and integration changes
- Repository coding conventions, layer boundaries, and architecture guard impact
- Step-by-step implementation sequence
- Unit test and integration test plan based on the actual repository test setup
- Verification commands or manual checks per repository
- Runtime profile / Dockerfile expectations per repository
- Rollback or release notes when rollout risk exists
- Risks, dependencies, and out-of-scope items

A valid technical plan should let the Development Loop implement without inventing new architecture.

## DC Checklist

The `DC Checklist` is a compact BA/QA/Developer walkthrough used after implementation to confirm the Story end to end. It is not a test-command list or a second status register.

Rules:

- Derive each item from confirmed Acceptance Criteria, Business Rules, relevant JIRA comments/images, and the actual repository behavior inspected during planning.
- Write each item as one short, observable, verifiable statement in the Story's primary language. It should say what is ready, what the user does, or what result is expected.
- Include only implementation-relevant preconditions such as source data readiness, scheduled synchronization, configuration, or permissions when BA/QA must confirm them before the primary flow can work.
- Cover the happy path, material combinations, persistence/read-back behavior, boundary/no-change behavior, integration freshness or failure behavior when relevant, and authorization/data-scope behavior when relevant.
- A checklist item may name a table, scheduled job, field, or API when it is a prerequisite BA/QA can verify. Do not list internal code edits, shell commands, or generic test tasks.
- Do not invent new scope. Every item must be traceable to the Story, confirmed clarification, JIRA context, or existing behavior that the change intentionally preserves.
- Keep it concise: normally 5-12 items. Merge duplicates rather than restating every AC verbatim.

Example:

```markdown
## DC Checklist

- [ ] 車型快照資料已更新，篩選下拉會顯示最新可用選項。
- [ ] 管理員可按 Brand、Class、Model 組合篩選消息受眾，三級選項會依規則連動。
- [ ] 未啟用車型受眾時，既有群組與手動名單的發送行為維持不變。
- [ ] 儲存後重新開啟消息，已選車型條件會正確回顯。
- [ ] 發送消息時，只觸達符合所有已選車型條件的用戶，且同一用戶不重複接收。
```

## Business Flow Diagram (Optional)

Use a Mermaid flowchart only when it helps a Developer understand a non-obvious business flow across systems, jobs, asynchronous steps, status transitions, or complex filtering. Do not add one for a simple local change. The diagram should describe business actors and flow, not class-level implementation.

## Plan Quality Bar

Reject your own draft and keep refining when:

- Steps say only "update service" without naming files or methods.
- A business term can map to more than one existing concept and the plan does not explicitly resolve the mapping.
- A non-trivial plan omits its flow and implementation interaction/class diagrams.
- The plan introduces a class, method, variable, API property, or persisted field without naming it and defining its relation to existing terminology.
- Verification says only "run tests" without naming the expected command or scenario.
- A repository is listed but has no concrete change list.
- Business scope changed but `story.md` was not updated.
- Security, permissions, migration, runtime, or rollback impact is unclear.
- A data relationship is modeled with a database foreign key.
- The plan changes a protected flow without naming its actor, permission/data scope, and verification approach.
- The plan ignores an existing architecture guard or claims tests that the repository does not actually support.
- The plan assumes Docker commands when the repository does not provide or reference a usable Dockerfile/profile.
- The plan asks App/PHP projects to run heavy environment-dependent builds when only syntax/light checks are expected.

## Approval (Feishu conversation only)

The approval prompt is an interaction with the user, not a section of the technical plan. Never write `## Approval`, `## Technical Plan Approval`, the approval status explanation, or the A-F choices into `technical-plan.md`. Save only the plan content in that file, then send the approval question as ordinary Feishu text. If the user requests a PDF, attach the plan without this conversational approval block.

Before setting `technicalStatus` to `approved`, ask:

```text
The technical plan is ready for review. What should I do next?

A. Approve and push the technical plan (Recommended)
B. Run local build / verification now, then decide
C. Approve, push the technical plan, and start build
D. Keep refining the plan
E. Return to business clarification
F. Other: describe what to do
```

Rules:

- Do not set `approved` without explicit user confirmation.
- If the user changes business scope, set `businessStatus` to `changed` and return to the Business Loop.
- If the user requests plan edits, keep `technicalStatus` as `draft`.

## Technical Status

Valid `technicalStatus` values:

- `draft` - the technical plan is being created, refined, questioned, or reviewed. This is the only non-approved state.
- `approved` - the user approved the technical plan; Development Loop may start.

If the story changes after approval, move `technicalStatus` back to `draft` and revise the plan. If planning is blocked, keep `draft` and record the blocker in `technical-plan.md` under `Risks` or `Technical Clarifications`.

## Language

Write `technical-plan.md` in the same primary language as `story.md` unless the user asks otherwise. Keep code identifiers, API names, repository names, and JIRA keys in their original form.
