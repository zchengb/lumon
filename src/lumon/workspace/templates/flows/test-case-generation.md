---
id = "test-case-generation"
name = "Test case generation"
enabled = true
brief = "Generate executable manual test cases from a story and its acceptance criteria."
match = ["generate test cases", "create test cases", "测试用例", "測試用例"]
---

# Test case generation

## When to use

Use this flow when the user asks to generate or review manual test cases for a story, bug, or acceptance criteria.

## Inputs and evidence

1. Extract the issue key or URL from the request.
2. Read `stories/<issue-key>/story.md` when available.
3. Inspect relevant repositories and existing tests under `repos/`.
4. If sufficient story or acceptance-criteria evidence is unavailable, ask the user for it.

## Process

1. Treat acceptance criteria as the primary authority.
2. Split each independently verifiable rule into one or more executable cases.
3. Generate only scenarios justified by the requirements or available evidence.
4. Keep UI cases tied to concrete pages, screens, elements, states, or navigation.
5. Use concrete actions and observable pass/fail results.
6. Do not invent permissions, limits, errors, or boundary values.
7. Validate that every case has acceptance-criteria references, steps, expected results, and a canonical case type.
8. Remove duplicate titles and reject placeholder steps.

## Tools and commands

- Inspect the Workspace and repository evidence before choosing a command.
- Use the existing Workspace tools and commands available to Codex.
- Do not put credentials, tokens, passwords, or private keys in generated artifacts.
- Do not claim that an external source was read unless a configured tool or command actually returned it.

## Output

Write:

- `lumon/artifacts/test-cases/<issue-key>.json`
- `lumon/artifacts/test-cases/<issue-key>.md`

The JSON root must contain `test_cases`. Each case must contain:

`ac_refs`, `title`, `feature_point`, `preconditions`, `steps`, `expected_results`, `case_type`, and `rationale`.

Allowed case types:

`functional`, `navigation`, `filter`, `permission`, `validation`, `state_transition`, `boundary`, `empty_state`, `ui`, `compatibility`.

Reply with the generated count, skipped or rejected count, source evidence, and artifact paths.
