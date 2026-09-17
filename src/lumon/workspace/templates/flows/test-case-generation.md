---
id = "test-case-generation"
name = "Test case generation"
enabled = true
brief = "Generate executable manual test cases from a story and its acceptance criteria."
match = ["generate test cases", "create test cases", "测试用例", "測試用例"]
---

# Test case generation

## Purpose and scope

Use this flow when the user asks to generate or review manual test cases for a
Story, Bug, or acceptance criteria. Generate business-facing, executable manual
cases. Treat acceptance criteria as the primary authority; then use the Story,
business rules, confirmed clarifications, and user-visible evidence.

Technical-only coverage belongs to another Agent. Do not create a case only
because a Technical Plan or repository mentions an API, endpoint, database
field, serializer, HTTP status, unit test, or implementation task. Technical
details may help locate the affected screen or flow, but must not expand,
narrow, or replace the business requirement.

The Workspace `AGENTS.md` is an execution constraint, not a substitute for the
Story's product requirements. The legacy test-case rules from the previous
Lumon implementation are historical reference only; this flow must not depend
on that old code being present.

## Output destination gate

Resolve the destination before generating cases:

1. If the request explicitly says to output directly, use direct mode.
2. If the request contains a Feishu Spreadsheet/Sheet link, use that link as
   the destination.
3. If neither is specified, ask in the user's language and stop:
   `請選擇測試用例輸出方式：1. 直接輸出在本次對話；2. 寫入既有飛書 Sheet。若選 2，請提供 Sheet 連結。`
4. If the user asks for Feishu output but does not provide a link, ask only for
   the link. Do not silently use a saved default destination.
5. Do not write to Feishu, Jira, a repository, or the Workspace before the
   destination is explicit. If no authorized Feishu Sheets capability is
   available, do not claim that a Sheet was written; ask the user to switch to
   direct mode or provide an available connection.

## Evidence and intake

1. Extract the issue key or URL. The default scope is one Story or Bug; when
   the user explicitly requests multiple issues, process each independently
   and report results per issue.
   If the user explicitly requests a `Ready for QA`/`Ready for Test` batch and
   a connected Jira source is available, discover the matching issues there;
   otherwise ask for the issue keys or local Story evidence. Do not infer a
   batch from an unqualified mention of QA.
2. Read `stories/<issue-key>/story.md` when present. If a connected Story/Jira
   source is available, read the supplied issue through that source. Never
   claim to have read a remote source unless a tool actually returned it.
3. Read acceptance criteria, business context, business rules, confirmed
   clarifications, screenshots, and named design references. Inspect relevant
   repositories and existing tests under `repos/` only to confirm the actual
   user-facing page, screen, element, state, or navigation.
4. If the Story or acceptance criteria do not provide enough evidence for an
   executable case, ask one focused question and do not generate placeholders.
5. For a Bug, use the confirmed business symptom and expected behavior; do not
   invent a root cause or technical regression case.

## Case design rules

For each independently verifiable business rule:

1. Create one case for one primary behavior. Split a rule only when the
   resulting behaviors can be verified independently.
2. Generate only scenarios justified by the requirements or evidence. Do not
   mechanically create positive, negative, and boundary cases for every rule.
3. Add negative, permission, empty-state, or validation cases only when the
   failure behavior is specified or strongly implied by a confirmed business
   rule. Add a boundary case only when a real boundary dimension is known.
4. Make every step a concrete user action and every expected result observable
   and pass/fail decidable. UI cases must name the relevant page/screen, state,
   element, displayed value, style, or navigation result.
5. Use a concise product surface for `feature_point` (for example `Admin
   Portal`, `Mobile App`, `App`, or `Web`), never an API, backend, database, or
   repository name.
6. Use canonical `case_type` values only:
   `functional`, `navigation`, `filter`, `permission`, `validation`,
   `state_transition`, `boundary`, `empty_state`, `ui`, `compatibility`.
7. Every case must include its `ac_refs`, title, feature point, preconditions,
   concrete steps, observable expected results, case type, and a short
   evidence-based rationale. Reject duplicate titles and generic placeholder
   steps. Do not invent permissions, limits, error messages, or test values.

## Sheet template contract

The existing target Sheet's header, order, formatting, and dropdowns are the
source of truth. Do not introduce a second schema. The legacy-compatible
baseline is the following exact A:O order:

| Column | Header | Populate with |
| --- | --- | --- |
| A | `卡link` | Verified source issue link; leave blank when none is available |
| B | `卡號標題` | `<issue-key> · <Story title>` |
| C | `设备/功能点` | Business-facing product surface |
| D | `用例 ID` | `TC-001`, incrementing within the Story tab/output |
| E | `Path` | See the mapping below |
| F | `Test Summary` | Concise business behavior under test |
| G | `Pre-condition` | Required account, data, and starting state |
| H | `Test Data` | Leave blank; put required data/state in G or I |
| I | `Action` | Numbered concrete manual actions |
| J | `Expected Result` | Observable result for each action/outcome |
| K | `测试人` | Leave blank |
| L | `測試結果` | `待驗證` |
| M | `測試日期` | Leave blank |
| N | `備註` | Leave blank |
| O | `Follow up` | Leave blank |

`ac_refs`, `case_type`, and `rationale` remain generation/traceability metadata;
do not add columns for them. In direct mode, include the references and short
rationale below the table. In Feishu mode, use `case_type` only to derive
`Path` unless the supplied template already has a traceability field.

Map canonical case types to the Sheet `Path` dropdown as follows:

- `functional`, `navigation`, `ui` → `Happy`
- `filter`, `state_transition`, `compatibility` → `Alternative`
- `permission`, `validation`, `empty_state` → `Sad`
- `boundary` → `Sad(Edge)`

Preserve the template's `Path` options (`Happy`, `Alternative`, `Sad`,
`Sad(Edge)`), result options (`待驗證`, `驗證成功`, `驗證失敗`, `忽略`),
header row, freeze behavior, and existing formatting. If a non-empty target
Sheet has a different header, stop and ask the user instead of mixing layouts.

## Generation and write process

1. Normalize the Story and acceptance criteria into a small case matrix before
   writing anything.
2. Draft cases using the business rules above, then validate references,
   completeness, case types, concrete actions, observable results, and title
   uniqueness.
3. In direct mode, return the generated rows in Markdown using the same A:O
   order and blank-cell rules, followed by generated/skipped counts, rejection
   reasons, and source evidence. Do not create a Feishu object.
4. In Feishu mode, use the supplied Sheet link. Read the existing template and
   rows first. Use or create a Story-specific tab named
   `<issue-key> · <Story title>` without changing the template tab. Append new
   rows and deduplicate by `Test Summary`; never clear or overwrite existing
   rows unless the user explicitly requests replacement. Read back the header
   and written rows before reporting success.
5. Return the exact destination link, generated/created/skipped counts, source
   evidence, and any rejected cases. Do not expose credentials or claim a
   remote write without a successful tool result.
