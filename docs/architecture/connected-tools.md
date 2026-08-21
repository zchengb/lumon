# Connected Tools

Connected tools are provider-native capabilities. Cursor, OpenCode, and Codex
receive a generated manifest and MCP-compatible stdio configuration inside the
Agent World. Agents call tools such as `jira.search`, `jira.update`, and
`feishu.file` through the provider's native tool mechanism; Lumon does not ask
the model to print an XML action envelope.

The Host still owns identity, entry-gate context, receipts, and transport. A
native call carries the Host-bound Gate capability into the tool bridge. The
Broker validates that binding and records the receipt, but does not repeat the
conversation's business authorization for every action. Direct CLI calls keep
the legacy authorization path and are not considered Agent-native calls.

The stdio server supports `initialize`, `tools/list`, and `tools/call`. Without
an entry-gate context it refuses calls rather than guessing an actor.
