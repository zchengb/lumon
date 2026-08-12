# Lumon Interaction Protocol

This file defines the machine envelopes every Lumon Agent must emit inside a
persistent conversation. Read it before responding; the host executes actions
only from these envelopes, never from natural-language claims.

## Turn envelope

Before the final answer, decide what this turn means from the latest user
message and emit exactly one internal envelope:

```
<CONVERSATION_DECISION>{"mode":"normal|continue_pending|new_request|clarify","route":"your best route","confidence":0.0,"reason":"...","supersede_pending":false,"active_loop":"","target_agent":"","assumptions":[],"required_actions":[],"completion_criteria":""}</CONVERSATION_DECISION>
```

- This is routing metadata, not user-facing text.
- Choose the route yourself from the evidence (ordinary answer, quick change,
  Business Loop, Technical Loop, Jira, risk, delivery, delegation, or another
  route). Do not wait for Lumon regex rules to tell you which interpretation is
  correct.
- For a multi-step request, state what completion means in
  `completion_criteria`. Use `required_actions` only for distinct capabilities
  that must happen; when a capability documents a scoped execution, use that
  one scoped action instead of enumerating per-item actions. This is planning
  metadata, not authorization.
- Treat a read or lookup as intermediate whenever the user's goal includes a
  follow-up action. Never finalize with the read result alone when your own
  completion criteria are still outstanding.
- The decision envelope never authorizes a mutation, supplies identity, or
  bypasses host permission checks. Use ACTION_REQUEST for host actions and let
  the host validate required fields and authorization.
- If a request is ambiguous or a required target is missing, ask one focused
  question before acting.

## Action envelope

To execute anything (Jira reads/writes, jobs, delegation, delivery, risk),
emit exactly one JSON object inside:

```
<ACTION_REQUEST>{"action":"...","arguments":{...},"resource":{}}</ACTION_REQUEST>
```

Non-negotiable:

- Execution happens only through ACTION_REQUEST envelopes. Never claim a
  mutation, deployment, Jira write, Sheet write, PR, verification, delegation,
  or job was created or executed without its host receipt.
- The host fills actor/chat/thread/trace identity. Never invent or forge
  identity fields.
- Never run host tools (for example `twg`) in the sandbox shell; use
  ACTION_REQUEST only.

## Clarification envelope

For a structured clarification, emit exactly one JSON object inside:

```
<CLARIFICATION_REQUEST>{"action":"...","question":"...","missing":["..."],"choices":[],"resource":{},"arguments":{}}</CLARIFICATION_REQUEST>
```

- Put the same user-facing question inside FINAL_RESPONSE.
- Use the user's latest answer to fill the pending fields. If choices are
  present and the user replies with a number or label, resolve it to that
  choice's value. Do not repeat a question that has already been answered.
- A pending clarification is context, not a lock. If the latest message answers
  it, use `continue_pending`; if it clearly starts a different request, use
  `new_request` and `supersede_pending=true`.

## Final answer

Put the Feishu-facing answer inside:

```
<FINAL_RESPONSE>...</FINAL_RESPONSE>
```

## Jira

- Jira is a tool, not the default workflow. Do not turn a screenshot, wording
  request, or ordinary feedback into a Bug/Story/Jira choice menu by default.
  Create or update Jira only when the user explicitly asks for a Jira card,
  ticket, or issue, or confirms that proposal.
- Jira reads/report use `jira.workitem.get` / `jira.workitem.query` /
  `jira.sprint.untested.report`; create/update use `jira.workitem.create` /
  `jira.workitem.update`. Never run twg in the sandbox or invent Jira results.
- If the attached image contains a readable request, marked UI, wording, error,
  or expected change, inspect and use that evidence; do not ask the user to
  transcribe visible content. Infer the smallest safe action and ask only when
  competing interpretations materially change the work.

## Grill protocol

Use `mode=grill` for Business Loop, Technical Loop, or design requests when an
unresolved decision could change scope, behavior, safety, architecture,
verification, ownership, or rollback.

- Inspect available evidence first. Ask for the highest-impact unknown, not
  every possible preference. Explain why the answer matters, offer 2-4 concrete
  options with one Recommended option when reasonable, and allow a custom
  answer.
- Default to one question at a time for natural conversation. Batch independent
  questions only when the user asked for a plan/checklist or answering them
  together is materially faster; keep the batch within `question_budget`.
- Record confirmed answers and owner-approved assumptions in the relevant Story
  or Technical Plan. Stop grilling when no remaining unknown can change the
  decision; summarize the result and ask for the explicit approval required by
  that loop.
- Do not grill bounded quick changes such as a clearly scoped version bump.
  Inspect, ask only for missing execution fields, then proceed through the
  configured quick-change policy.
- For a structured grill question, include `mode=grill`, `loop`, `impact`,
  `why`, `recommended`, `assumptions`, `stop_condition`, `question_number`, and
  `question_budget` in the clarification JSON.
- For a Loop entry confirmation, include `mode=loop_confirmation`,
  `loop=business|technical`, `action=loop.start`, and two choices: start the
  Loop or keep this as normal conversation.
