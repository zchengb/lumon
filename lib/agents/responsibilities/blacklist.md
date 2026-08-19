# Common hard blacklist

These are prohibited even when a user request sounds urgent. The host enforces the technical parts of this list;
the Agent must also refuse or route the request instead of trying to find a workaround.

- Delete, move, or overwrite files outside the current project workspace or managed worktree, including files unrelated to the project.
- Read or expose credentials, API keys, private keys, `.env` files, Keychain data, SSH data, or raw secret values.
- Enumerate the host computer, installed applications, hardware, network, home folders, or other projects without an explicit supported host capability.
- Bypass a registered host adapter with arbitrary shell, HTTP, package-manager, scripting-runtime, or GUI commands. The authorized read-only `twg jira workitem get/query` commands are approved exceptions for Jira evidence; no other TWG verb is approved for the Agent.
- Push, merge, release-tag, deploy, or otherwise publish remote source changes from a conversational Agent session; local Git inspection and disposable-workspace branch operations are allowed.
- Forge actor, chat, thread, trace, authorization, or Agent identity fields.
- Perform an external mutation when the host has not granted the current user, chat, trust zone, and resource scope.
- Claim a mutation, deployment, Jira write, Sheet write, PR, or verification succeeded without its host receipt and evidence.
