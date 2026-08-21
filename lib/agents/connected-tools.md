# Native Connected Tools

Cursor, OpenCode, and Codex receive the connected-tool registry through the
workspace `.lumon/host-tools.json` file and the provider Harness.  A native
tool call is named directly (for example `jira.update`, `bitable.write`, or
`feishu.file`); it does not need an `ACTION_REQUEST` wrapper or a
`FINAL_RESPONSE` marker.

The Host remains the safety boundary.  It injects the trusted conversation
identity, workspace boundary, credentials, audit receipt, retry policy, and
provider-neutral error.  Tool arguments must never contain raw credentials or
transport identity fields.

Conversation output is a runtime capability rather than a business action:

```text
conversation.message(text)
conversation.progress(text)
conversation.finding(text)
conversation.decision(text)
conversation.question(text, choices=[])
conversation.artifact(path)
```

Use `@Agent` for ordinary Thread collaboration.  The native registry keeps
`agent.job.create` only for durable background work that must survive a
conversation turn or process restart; it is not a substitute for a visible
handoff.

The legacy envelope catalog remains under `legacy_compatibility` only for
older provider/workspace configurations.  Native providers should prefer
ordinary Harness messages, native Questions, direct connected tools, and
visible `@Agent` handoffs.
