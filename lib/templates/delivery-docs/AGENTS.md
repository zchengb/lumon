# __PROJECT_NAME__ Agent Guide

This repository is the source of truth for business stories and technical delivery plans. It is also the delivery workspace root.

## Repository Model

Business topics live under `topics/`. Business stories live under `stories/`. Linked code repositories live under `repos/` and are gitignored by this docs project.

Each topic and story is intentionally lightweight:

- `topics/<slug>.md` - broad business discovery container before story split

Each story contains:

- `story.md` - business truth, maintained by humans with Agent help
- `technical-plan.md` - technical delivery plan, maintained during the technical loop
- `metadata.json` - status and machine-readable index, maintained by Lumen or explicit status commands
- `assets/` - images referenced by `story.md` or `technical-plan.md`

Do not create extra decision, question, change, refactor, or evidence files unless explicitly requested. Git diff, commits, PRs, JIRA comments, and Lumen logs are the default audit trail.

## Docs Repository Commit Format

When committing to this delivery docs repository (`stories/`, `topics/`, `standards/`, `AGENTS.md`, `lumen/config/`, and related docs), always use:

```text
[lumon] #{JIRA_KEY_OR_N/A} {chore|docs|feat|fix|refactor|style|test}: {summary}
```

Examples:

```text
[lumon] #N/A feat: update delivery config
[lumon] #MBPAS-1400 feat: update MBPAS-1400 delivery status
[lumon] #N/A docs: align business loop questioning rules
```

Rules:

- Always use the `[lumon]` prefix. Never use a human author prefix such as `[xiaobin]`, even when older history used one.
- Use the Story JIRA key when the change belongs to one Story; otherwise use `N/A`.
- Prefer `feat` for Story/docs/config updates unless another type is clearly better.
- Keep the summary short and concrete.
- Dashboard auto-commits for config and Observatory markdown already follow this format; agent commits must match it too.

## Business Loop

The Business Loop may run in Codex, Cursor, or another compatible Agent. The tool is not important; the contract is.

The Business Loop can start from a broad Topic or from a concrete Story. It turns unclear business input into either `topics/<slug>.md` plus candidate stories, or a clear `story.md`. Before starting the Business Loop, the Agent should refresh the workspace context:

- Pull this docs repository first.
- Pull every configured code repository that may be used as context. Repositories live under `repos/` and are discovered from `lumen/config/workspace.json`.
- Use safe git sync: check `git status` first, then run `git pull --ff-only` only when the repo has no local uncommitted changes.
- If any repo has local uncommitted changes or cannot fast-forward, stop and ask the user how to proceed. Do not stash, reset, checkout, or overwrite user work automatically.

During Topic Discovery, the Agent should:

1. Create or update `topics/<slug>.md` using `templates/topic.md`.
2. Read existing topics, stories, and relevant repository context.
3. Understand current system behavior before suggesting story splits.
4. Use the Lumen Grill protocol for consequential ambiguity: ask the highest-impact question, explain its consequence, offer options, and record the answer or an owner-approved assumption. Use one question at a time when answers depend on one another.
5. Record confirmed answers in the topic file.
6. Propose candidate stories only after enough context is understood.
7. Create story folders only after the user confirms the split.
8. Never modify application code.

During Story Clarification, the Agent should:

1. Read the existing `story.md` and `metadata.json`.
2. Inspect relevant repository context if available.
3. Ask focused questions for unclear business points.
4. Record clarified question-answer pairs in `story.md` under `Clarifications`.
5. Update `Background`, `Acceptance Criteria`, `Business Rules`, and `Out of Scope` as needed.
6. Place image files under `assets/` when needed, and reference them inline in the relevant section using relative Markdown links.
7. Never modify application code.
8. When the story becomes clear, ask whether to publish it to JIRA as a Story.

## JIRA Publication Rule

Docs are created first. JIRA is created or bound only after the business story is clear enough for confirmation.

When `businessStatus` is ready or the user confirms the story is ready, the Agent should ask one explicit question:

```text
The story looks business-ready. Should I create or bind a JIRA Story for it?

A. Create a new JIRA Story (Recommended)
B. Bind to an existing JIRA issue
C. Not now; keep it in docs only
D. Other: describe what to do
```

Rules:

- Do not create a JIRA issue without explicit user confirmation.
- Prefer Atlassian/JIRA MCP when available in the active Agent environment.
- If Atlassian/JIRA MCP is unavailable, use `twg-cli` / `twg jira` as the fallback.
- Before creating, discover required fields for the target JIRA project and Story issue type.
- Create issue type `Story` unless the user chooses another type.
- Use `story.md` as the source for summary and description; do not paste raw chat history.
- Write the JIRA description in a standard Agile Story format.
- After creation or binding, update `metadata.json.jiraKey`, `metadata.json.jiraUrl`, `metadata.json.jiraIssueType`, and `metadata.json.jiraPublishedAt`.
- Also update `jiraUrl` in the YAML front matter of `story.md`.
- Before a JIRA issue exists, do not prefix the `story.md` H1 or story folder name with a local story id that looks like a JIRA key. Use `# <Story Title>` for the H1 and a plain business slug for the folder name when possible.
- After a JIRA issue is created or bound, update the `story.md` H1 to `# <JIRA-KEY> <Story Title>` using the real JIRA key. Rename the story folder to `<JIRA-KEY>-<slug>` when it can be done without overwriting an existing folder.
- Add a short JIRA comment linking back to this docs story when supported.
- Verify the created or bound JIRA issue by reading it back and report the key and URL.

JIRA Story description format:

```markdown
## User Story
As a <user>,
I want <capability>,
so that <business value>.

## Business Context
<short background from story.md>

## Acceptance Criteria
<copy the ACs in Given/When/Then form>

## Business Rules
<copy confirmed business rules>

## Clarifications
<copy only confirmed Q&A that materially affects scope>

## Out of Scope
<copy explicit exclusions>

## Docs
<relative docs path or repository URL when available>
```

## Existing Jira Story Import And Consistency

For an existing Jira Story, invoke the `$lumen-jira-story-import` Agent Skill (or `lumen jira import <JIRA-KEY>`). It creates the linked Story folder on first use and records the current Jira payload under `lumen/context/`. On later use it reads Jira again without overwriting `story.md`. After import, continue directly into the Business Loop for that Story.

Before every Business or Technical Loop, invoke the import Skill when `metadata.json.jiraKey` exists and this turn has not already imported it. If `metadata.json.jiraSyncStatus` is `changed`, the Technical Loop must ask whether to reconcile Jira changes through the Business Loop, keep the local Story, or review the difference. A Jira change invalidates the technical plan but does not silently alter the locally confirmed business status. Only a confirmed reconciliation updates `story.md`; never overwrite it silently.

## Progressive Questioning Rule

During the Business Loop and Technical Loop, use the Lumen Grill protocol rather than a fixed questionnaire. Batch independent high-impact questions when the user asks for a plan or checklist; otherwise ask one question at a time when the next question depends on the previous answer. Never ask a question already resolved by workspace evidence.

Rules:

- Ask only unresolved questions that can change scope, actors, business rules, acceptance, failure behavior, architecture, verification, rollout, or rollback.
- Order questions by impact: scope, actors, rules, acceptance, failure behavior, then lower-impact details.
- Prefer interactive Q&A when the environment supports it.
- Each question should include 2-4 concrete options.
- Mark one option as `Recommended` when repository evidence supports it, explain the consequence, and allow a custom answer.
- Stop grilling when no remaining unknown can change the decision; summarize the result and ask the loop's explicit approval question.
- The Technical Loop approval question is Feishu conversation only. Never write `## Approval`, `## Technical Plan Approval`, or its answer choices into `technical-plan.md`; a requested PDF must contain the plan only.
- Always allow the user to provide a custom answer.
- Do not use blank placeholders as the primary interaction style.
- After the user answers, update `topics/<slug>.md` under `Progressive Clarifications` during Topic Discovery, or `story.md` under `Clarifications` during Story Clarification, and update `technical-plan.md` for technical answers.
- Ask a follow-up batch only for newly exposed high-impact gaps.

If the tool supports an interactive question UI, use it. If not, present a short text checklist like:

```text
Please answer all of the following in one reply.
For each question, choose a letter or type your own answer.

1. Question: Who configures the audience filter?
A. System configuration (Recommended)
B. Admin page configuration
C. Not decided yet; mark the story blocked
D. Other: describe your answer

2. Question: What happens when the source data is empty?
A. Show an empty state (Recommended)
B. Hide the section
C. Block publishing
D. Other: describe your answer
```

## Language Rule

Write `topics/<slug>.md` and `story.md` in the primary language of the user's business input by default. Do not force English or any other fixed language. Keep the story internally consistent in one main language unless the user explicitly asks otherwise. Preserve product names, domain terms, JIRA keys, code identifiers, API names, field names, and configuration names in their original form.

When creating or updating a JIRA Story from `story.md`, use the same primary language as `story.md`.

## Story Rules

`topics/<slug>.md` is allowed to be broader than a story, but it must stay business-readable. It should contain current understanding, repository context, progressive clarifications, candidate stories, risks, and out-of-scope notes.

`story.md` must be business-readable. It should contain only:

- YAML front matter metadata with `title` and `jiraUrl`
- Background
- Acceptance Criteria
- Business Rules
- Clarifications
- Out of Scope

Do not put delivery status in `story.md`. Do not put technical implementation details in `story.md`. Do not put raw chat history in `story.md`.

Title and folder rule: before JIRA publication, the H1 must be `# <Story Title>` without any local story id prefix, and the story folder should not use a fake JIRA-like prefix. After JIRA publication or binding, the H1 may become `# <JIRA-KEY> <Story Title>` and the story folder should become `<JIRA-KEY>-<slug>` using the real JIRA key.

If an edge case matters, express it as an Acceptance Criterion or Business Rule. Do not maintain a separate Edge Cases section by default.

## Metadata Rules

`metadata.json` is the status file. It contains:

- `storyId`
- `jiraKey` / `jiraUrl` / `jiraIssueType`
- `businessStatus`
- `technicalStatus`
- `deliveryStatus`
- `linkedRepos`
- `updatedAt`
- optional `logs` references

The explicitly invoked Business and Technical Loop skills may update the existing status fields in `metadata.json` after the required conversational confirmation. Do not add CLI approval commands.

## Business Status

Valid `businessStatus` values:

- `draft` - initial story exists but is incomplete
- `clarifying` - Agent is asking questions and refining scope
- `ready` - story is clear enough for technical planning
- `blocked` - story cannot proceed because required business input or external dependency is missing
- `changed` - story changed after technical planning started or after plan approval

## Technical Loop

The Technical Loop may run in Codex, Cursor, or another compatible Agent. Read `standards/technical-loop.md` for the full contract.

Frontend delivery is disabled. Do not approve or start a Story whose delivery includes Web, Native, mobile UI, frontend source changes, Figma-to-code work, browser/device runtime work, a Visual Delivery Contract, or visual QA. Keep that part out of scope or blocked; backend-only work may proceed only when it is independently deliverable without frontend changes.

Before starting the Technical Loop, use the same preflight sync rules as the Business Loop.

During the Technical Loop, the Agent should:

1. Read `story.md`, `metadata.json`, `templates/technical-plan.md`, and the Lumen coding guideline shipped with the CLI.
2. Inspect impacted repositories and identify real modules, endpoints, tables, jobs, Dockerfiles, build files, and tests.
3. If the input is a broad topic, guide the user to split and select one concrete story before planning.
4. Use the Lumen Grill protocol for unresolved technical questions affecting design, scope, runtime, verification, rollout, or rollback; ask sequentially when questions depend on one another and otherwise use a small checklist.
5. Offer concrete options for each question and allow a custom answer.
6. Record confirmed technical decisions in `technical-plan.md`; do not leave decisions only in chat.
7. Derive a concise, business-facing `Delivery Checklist` from confirmed Acceptance Criteria and Business Rules; do not use technical implementation language.
8. Add an optional business flow diagram only when the flow spans systems, jobs, asynchronous steps, state transitions, or complex filtering.
9. Produce a file-level plan detailed enough for implementation without guessing.
10. Save only the technical plan in `technical-plan.md`; ask whether to approve and push the plan, run build/verification now, or keep refining as ordinary Feishu text.
11. Ask for explicit user approval before setting `technicalStatus` to `approved`.
12. Never modify application code during the Technical Loop.

A technical plan is not ready until it is scoped to one story and includes repository scope, existing layer boundaries and coding conventions, architecture guard impact, file-level changes, API/schema/config/integration/permission impact, runtime profile, implementation steps, test strategy based on actual repo capabilities, verification, rollback, and out-of-scope boundaries. Database foreign keys are not allowed; plan application-level relationship validation and indexes instead.

## Technical Status

Valid `technicalStatus` values:

- `draft` - the technical plan is being created, refined, questioned, or reviewed. This is the only non-approved state.
- `approved` - user approved; Development Loop may start.

If the story changes after approval, move `technicalStatus` back to `draft` and revise the plan. If planning is blocked, keep `draft` and record the blocker in `technical-plan.md`.

## Development Loop

The Development Loop is executed by `lumen delivery run`. Read `standards/development-loop.md` for the full contract.

Coding standards are shipped with the Lumen CLI and injected automatically during `lumen delivery run`. Do not copy the coding guideline into the docs repository. The delivery Agent must first discover the impacted repository's actual layer boundaries, coding conventions, test capability, architecture guards, and authorization patterns; those repository-specific facts govern implementation.

Do not start the Development Loop until:

- `metadata.json.businessStatus` is `ready`
- `metadata.json.technicalStatus` is `approved`
- `technical-plan.md` is detailed enough for file-level implementation

During the Development Loop, Lumen CLI should:

1. Read the approved `technical-plan.md`, `story.md`, and `metadata.json`.
2. Resolve code repositories from the configured workspace mapping.
3. Create feature worktrees under `<workspace-root>/lumen/worktrees/<story-key>/<repository>/`.
4. Run the delivery agent with the Lumen coding guideline.
5. Let Lumen run verification after the Agent exits. Java uses host JDK/Testcontainers when required; App/PHP stay on lightweight checks. Frontend delivery is rejected before worktree creation.
6. If mandatory verification fails, Lumen may invoke up to two bounded remediation rounds in the same worktree. Each round receives the failed-check evidence and may make only the smallest Story-scope correction. Lumen stops for human review after the configured limit.
7. Record a repository-history-compatible `commit_subject` in `delivery-result.json`, but do not commit, push, or open a PR.
7. Let Lumen commit, push, open PRs, update `metadata.json.deliveryStatus`, transition JIRA, send notifications, and archive the run.

## Delivery Status

Valid `deliveryStatus` values:

- `not_started` - plan approved but no code work yet
- `in_progress` - implementation is underway
- `blocked` - cannot proceed because of environment, dependency, or missing decision
- `dev_done` - code complete locally but no PR yet
- `pr_open` - PR created and awaiting review or merge
- `done` - change merged or accepted as complete

## Coding Standards

Development execution uses the Lumen CLI coding guideline at `lib/standards/coding-guideline.md`.

Run implementation with:

```bash
lumen delivery run --story <JIRA-KEY-or-slug>
```

Interactive technical planning may still run in Codex or Cursor, but code implementation should go through `lumen delivery run` once `technicalStatus` is `approved`.

## Change Handling

Business changes are reflected directly in `story.md` and reviewed through Git diff. Do not create separate CR files by default.

Refactors are discussed in the development tool and reviewed through code diff or PR description. Do not create separate RF files by default. If a refactor changes architecture or public API behavior, record it in `technical-plan.md` under `Refactoring Notes`.

## Agent Response Format

Every Agent response should include:

### Evidence
Files or repository facts used.

### Clarifications
Questions asked and answers recorded.

### Changes Made
Files changed.

### Risks
Remaining ambiguity or risk.

### Next Step
Recommended next action.
