<!-- Lumen managed: agent-skill -->

# Business Loop workflow

The Feishu Loop Gateway is an accepted entry point. A clear natural-language request to create, capture, or turn material into a requirement or Story starts this workflow directly; an ambiguous request gets one confirmation. The gateway never authorizes technical planning or delivery.

Preflight: safely refresh the docs and relevant clean repositories; stop for local changes or non-fast-forward history. For a Story with `metadata.json.jiraKey`, invoke `$lumen-jira-story-import` before reading requirements unless this turn already imported that Story. If `jiraSyncStatus` is `changed`, include reconciliation in the first question batch, then update `story.md` only after confirmation. Set `jiraSnapshotHash` to `jiraLatestSnapshotHash` and `jiraSyncStatus` to `synced` with the confirmed Story update. Never change application source code.

For a Topic, inspect existing stories and repository context, then use the Lumen Grill protocol: identify the highest-impact unknowns first, explain what each answer changes, offer concrete options with a recommended default when reasonable, and allow a custom answer. Ask one question at a time for natural conversation; batch independent questions only when the user asked for a plan/checklist or the answers do not depend on one another. Record confirmed answers and owner-approved assumptions. Propose Story candidates only when understood. Split by independently understandable and independently verifiable business outcomes: one primary goal, observable outcome, independent verification and delivery (or a stated dependency), explicit boundary, no duplicated business rule, and no unrelated actors/workflows. Split by business outcome, not frontend/backend/database layers unless those separately deliver an outcome. Present title, business goal, acceptance boundary, dependencies, and excluded scope. Do not create folders until the user confirms the split.

For a Story, update only business material: Background, Acceptance Criteria, Business Rules, Clarifications, and Out of Scope. Grill only on decisions that can change scope, user-visible behavior, actors, permissions, failure behavior, timing, or acceptance criteria; do not ask cosmetic questions and do not repeat evidence-backed facts. Before changing `metadata.json.businessStatus` to `ready`, confirm there is no important TBD or unresolved high-impact question and present: goal, primary actor, key rules, AC summary, out of scope, and non-blocking assumptions. Ask exactly:

```text
A. Confirm this Story and mark it ready
B. Continue refining
C. Keep it as draft
```

Only A or equally explicit natural-language confirmation may set `businessStatus` to `ready`. Then offer the existing explicit Jira create/bind step. Do not create Jira issues without confirmation.
