# Business Loop

The Business Loop supports two entry shapes: a broad Topic or a concrete Story. A Topic is used when the user starts from an area, idea, customer request, or vague business problem. A Story is used when the scope is already small enough to express as ACs. The loop can be run in Codex, Cursor, or another Agent.

## Inputs

- Initial business topic, idea, customer request, story text, or JIRA description
- Existing `topics/<slug>.md` if the work starts from a broad topic
- Existing `story.md` if the work starts from a concrete story
- Relevant code/repository context when useful
- Optional screenshots or sketches placed under `assets/` and referenced inline where they are discussed

## Outputs

For Topic Discovery:

- Updated `topics/<slug>.md`
- Candidate story split proposal

For Story Clarification:

- Updated `story.md`
- Updated `metadata.json.businessStatus` through Lumen or explicit status update

## Preflight Sync

Before starting the Business Loop, refresh the workspace context:

1. Pull this docs repository first.
2. Pull every configured code repository under `repos/` that may be used as context.
3. For each repo, check `git status` before pulling.
4. Run `git pull --ff-only` only when the repo has no local uncommitted changes.
5. If a repo has local uncommitted changes, diverged history, or cannot fast-forward, stop and ask the user how to proceed. Do not stash, reset, checkout, or overwrite user work automatically.

## Topic Discovery Flow

Use this flow when the user starts with a broad topic instead of a concrete story.

1. Create or update `topics/<slug>.md` using `templates/topic.md`.
2. Read the topic, existing stories, and relevant repository context under `repos/`.
3. Build a short understanding of current system behavior before proposing story splits.
4. Use the Lumen Grill protocol: inspect evidence first, ask the highest-impact unknowns, explain what each answer changes, offer options with a recommended default when reasonable, and allow custom answers. Ask one question at a time when answers depend on each other; batch independent questions only when the user asks for a plan/checklist.
5. Record confirmed answers under `Progressive Clarifications`.
6. Gradually identify candidate stories with clear goals and boundaries.
7. Do not create story folders until the user confirms the split.
8. When the user confirms one candidate story, create a normal `stories/<slug>/` folder from `templates/story.md` and continue with the Story Clarification Flow.

A Topic is not implementation-ready. It is a discovery container. Lumen must not start Technical Loop or Development Loop from a topic directly.

## Story Clarification Flow

1. Start from draft story input, a confirmed candidate story from Topic Discovery, or a Story just imported from Jira.
2. Agent reads `story.md`, `metadata.json`, related topic notes if any, and relevant repository context.
3. Agent identifies every remaining high-impact unclear point and removes questions already answered by evidence.
4. Agent grills only on decisions that can change scope, user-visible behavior, actors, permissions, failure behavior, timing, or acceptance criteria. Ask sequentially when dependent; otherwise use a small checklist batch.
5. User answers the checklist in one reply, choosing options or entering custom answers.
6. Agent records the clarified Q&A under `Clarifications`.
7. Agent updates Acceptance Criteria and Business Rules when needed.
8. Agent asks a follow-up batch only if new high-impact ambiguity remains.
9. When clear, present the Story goal, primary actor, key business rules, Acceptance Criteria summary, Out of Scope, non-blocking assumptions, and confirmation that no important TBD or high-impact question remains. Ask: `A. Confirm this Story and mark it ready`, `B. Continue refining`, or `C. Keep it as draft`.
10. Set `businessStatus` to `ready` only after option A or equally explicit natural-language confirmation; the Agent's readiness assessment is not approval.
11. Ask whether to create or bind a JIRA Story.
12. If confirmed, create or bind JIRA and write the result to `metadata.json`.

## Language

Use the primary language of the user's business input for `topics/<slug>.md` and `story.md`. Do not force English, Chinese, or any fixed language. Keep product names, domain terms, JIRA keys, code identifiers, API names, field names, and configuration names in their original form.

JIRA Story content created from `story.md` should use the same primary language as `story.md`.

## Progressive Q&A

A Business Loop question must be concise and answerable. Prefer interactive Q&A if supported by the environment. Every Grill question states its impact, gives 2–4 options with one recommended default when reasonable, and permits a custom answer. Stop when no remaining unknown can change the Story decision; do not turn low-impact preferences into blockers.

Question format:

```text
Please answer all of the following in one reply.
For each question, choose a letter or type your own answer.

1. Question: <focused question>
A. <recommended option> (Recommended)
B. <alternative option>
C. <block/defer option when useful>
D. Other: type a custom answer

2. Question: <next focused question>
A. ...
B. ...
C. ...
D. Other: type a custom answer
```

Rules:

- Ask all remaining high-impact questions in one turn unless the user asks for progressive single-question mode.
- Ask the questions that most affect scope, architecture, or acceptance first.
- Provide 2-4 meaningful options per question.
- Always allow a custom answer.
- Do not ask users to fill blank templates.
- Record the final answers in `topics/<slug>.md` during Topic Discovery or in `story.md` during Story Clarification. Do not keep raw chat history.

## JIRA Publishing

The docs story is the starting point. JIRA should be created or bound after the story is business-ready, not before.

Ask the user:

```text
The story looks business-ready. Should I create or bind a JIRA Story for it?

A. Create a new JIRA Story (Recommended)
B. Bind to an existing JIRA issue
C. Not now; keep it in docs only
D. Other: describe what to do
```

Behavior:

- Do not create JIRA without explicit confirmation.
- Prefer Atlassian/JIRA MCP when available.
- If Atlassian/JIRA MCP is not available, use `twg-cli` / `twg jira` fallback.
- Discover required JIRA fields before creation.
- Create issue type `Story` by default.
- Use `story.md` as the source for JIRA summary and description.
- Write the JIRA description in standard Agile Story format:
  - User Story
  - Business Context
  - Acceptance Criteria in Given/When/Then form
  - Business Rules
  - Clarifications that materially affect scope
  - Out of Scope
  - Docs link or docs path
- After create or bind, update `metadata.json` with the JIRA key, URL, issue type, and publish time.
- Also update `jiraUrl` in the YAML front matter of `story.md`.
- Before JIRA exists, keep the `story.md` H1 as `# <Story Title>` without a local story id prefix, and do not use a fake JIRA-like prefix in the story folder name.
- After create or bind, update the H1 to `# <JIRA-KEY> <Story Title>` and rename the story folder to `<JIRA-KEY>-<slug>` using the real JIRA key when it can be done safely.
- Verify by reading the JIRA issue back.

## Readiness

A story is business-ready when:

- Acceptance Criteria are clear and testable.
- Important business rules are explicit.
- Clarifications contain answers for previously unclear points.
- Out of Scope prevents obvious overbuild.
- No important `TBD` remains.
- User explicitly confirmed the Story should be marked ready.
