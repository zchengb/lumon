# Native Connected Tools

The registry is a provider-neutral capability map, not a second permission
controller. The Feishu entry gate establishes who may use the current
conversation; the Agent chooses which connected tool or local CLI is useful.
Lumon records identity, arguments, receipt, and result for audit.

Cursor, OpenCode, and Codex receive the connected-tool registry through the
workspace `.lumon/host-tools.json` file and the provider Harness.  A native
tool call is named directly (for example `jira.update`, `bitable.write`, or
`feishu.file`); it does not need a provider transport envelope.

The Host remains the identity, trust-gate, and audit boundary. In the default
trusted dedicated-machine mode it does not replay or wrap the provider's
native tool call in a legacy action request, and it does not impose a role
action ACL. Tool arguments must never contain raw credentials or transport
identity fields.

Conversation output is a runtime capability rather than a business action:

```text
conversation.message(text)
conversation.progress(text)
conversation.finding(text)
conversation.decision(text)
conversation.question(text, choices=[])
conversation.artifact(path)
```

The registry also exposes `feishu.context`, a read-only Agent-readable view of
the current conversation. It may include the context type (`dm`, `group`, or
`thread`), chat and Thread identifiers, chat name, known participants, and
reachable Agent apps. `available_agents_verified` distinguishes Agent apps
confirmed through Feishu group visibility from names merely observed in a
mention. It exists so the Agent can make an informed collaboration choice; it
does not grant or deny access and must not be treated as a second permission
controller.

Conversation quality is a judgment seam, not a hard controller: investigate
quietly by default, use Typing for ordinary work, choose Consult versus
Transfer deliberately, prefer live incident evidence, and calibrate what is
confirmed versus still unknown.

Use `@Agent` for ordinary Thread collaboration.  The native registry keeps
`agent.job.create` only for durable background work that must survive a
conversation turn or process restart; it is not a substitute for a visible
handoff.

The legacy envelope catalog remains under `legacy_compatibility` only for
older provider/workspace configurations. Native providers should prefer
ordinary Harness messages, native Questions, direct connected tools, normal
CLI capabilities, and visible `@Agent` handoffs. A native MCP tool event is
already executed exactly once by the Host dispatcher; Harness events record
it for audit and must never be replayed as a second action.
