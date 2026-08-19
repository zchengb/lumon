<!-- Lumen managed: agent-skill -->

# Technical Loop workflow

This loop is never the first stage of a combined Story Plan + Technical Plan request. It may start only after the Story/Business Loop has produced `story.md` and `metadata.json.businessStatus=ready`. If that prerequisite is absent, return to Business Loop and keep the user-facing explanation in text; do not generate a PDF or present a technical plan.

The Feishu Loop Gateway is an accepted entry point. A clear natural-language request to turn a business-ready requirement or Story into a technical plan/design starts this workflow directly; an ambiguous request gets one confirmation. The gateway never authorizes delivery or code changes.

Frontend delivery is disabled. Do not plan or approve Web, Native, mobile UI, frontend source, Figma-to-code, browser/device runtime, Visual Delivery Contract, or visual QA work. Keep it out of scope or blocked and return to the Business Loop if the Story cannot be delivered without frontend changes. Backend-only work may proceed only when it is independently deliverable without frontend changes.

Preflight safely refreshes the docs and relevant clean repositories. For a Story with `metadata.json.jiraKey`, invoke `$lumen-jira-story-import` before reading requirements. If `jiraSyncStatus` is `changed`, ask exactly: `Jira changed since this Story was confirmed. A. Pull and reconcile the Jira changes in the Business Loop B. Keep the local Story and continue technical planning C. Review the difference first`. Only A returns to the Business Loop; B is an explicit local-source decision and may continue planning. Gate on one Story with `businessStatus: ready`; keep `technicalStatus` as `draft` until explicit approval. Inspect real repositories, build/test setup, permission patterns, and affected modules before planning. Never modify application source code.

Recommend a profile, explain why, and let the user override. Use the five-section structure in `templates/technical-plan.md`: Scope & DC Checklist; Baseline & Decisions; Design & Architecture; Change Contract & Implementation; Verification, Performance & Delivery. **Light** is one localized repository change with no public API, migration, authorization/data scope, integration, async/scheduled change, or meaningful rollback risk; keep the plan short and omit diagrams when they add no clarity. **Standard** is normal moderate impact; include the diagrams, contracts, and conditional sections that the change actually needs. **Complex** applies to multi-repository, migration/backfill, permissions/data scope, public/cross-service API, integrations, async/scheduled flow, state machine, high rollback risk, or significant placement decisions. Complex plans must include an end-to-end Mermaid flowchart, a class/component diagram, the full identifier contract, dependency-ordered file changes, performance assessment, and rollback/release order. Do not add a "why this is complex" section or irrelevant boilerplate.

Use the Lumen Grill protocol for remaining high-impact technical decisions. Ask one question at a time when the next answer depends on the previous answer; otherwise batch up to four independent questions when the user asked for a plan/checklist. Every question should state the decision impact, offer 2–4 options with one `Recommended` when reasonable, and allow a custom answer. Do not ask questions already answered by repository evidence, and record owner-approved assumptions instead of reopening settled decisions.

For important decisions, add concise repository evidence: decision, `repository/path → symbol` (with an optional stable line range), and what it proves. Use a 3–8 line excerpt only when path and symbol are insufficient.

For any query, collection, batch, API, asynchronous job, scheduled flow, integration, or large UI list, assess performance before approval: current and expected data volume, growth, call frequency, concurrency, latency/timeout expectations, result bounds, indexes, pagination, batching, caching, idempotency, resource usage, and failure behavior. Prefer existing evidence such as query plans, indexes, metrics, repository conventions, or measured timing. Never invent precise scale or latency values. If an unknown could change the design, ask a batched Technical Loop checklist question covering: (A) data volume and growth, (B) frequency/concurrency, (C) latency or SLA, and (D) available index/measurement evidence. Keep the plan draft until resolved or explicitly recorded as an owner-approved assumption. If the change is demonstrably local and performance-neutral, record `No material performance impact` with the reason.

For Complex plans, enumerate every new or changed method, API property, persistence field, DTO property, UI state, and semantic local/query variable in the Identifier Contract. Reuse existing names when the concept is unchanged. Add failure, retry, migration, permission, and rollback behavior to the same implementation contract; do not leave these decisions only in chat.

If repository facts expose a business ambiguity affecting ACs, rules, user-visible behavior, actors/roles, permission/data visibility, scope, failure behavior, or promised freshness/timing/availability: keep technical status draft, show evidence and business options/consequences, ask the owner/BA to run Business Loop, and resume only after `story.md` changes and business status is ready. Do not alter `story.md` yourself. Pure implementation decisions belong in the plan.

For a Story that cites a Figma URL or requires frontend/UI work, do not inspect or implement the UI in this loop. Record the frontend portion as out of scope or blocked; do not create a Visual Delivery Contract or approve a plan that includes it.

Before approval, complete repository investigation, selected profile, questions, concrete verification, and the quality bar; no blocking TBD. Present profile/reason, repositories, approach, architecture/domain decisions, applicable data/API/permission/integration/runtime impact, verification, risks, and out-of-scope. Ask exactly:

```text
A. Approve this Technical Plan
B. Continue refining
C. Keep it as draft
D. Request a Business Loop revision
```

Only explicit A may set `metadata.json.technicalStatus` to `approved`. A substantive approved-plan change returns it to draft and requires approval again; typographical or formatting-only changes do not.
