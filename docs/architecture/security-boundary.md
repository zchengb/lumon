# Security Boundary

Lumon's security boundary has four layers:

1. **Ingress gate** — Feishu identity, chat/thread scope, agent role, and
   access policy are evaluated once when a message enters the Host.
2. **Agent World** — the provider sees only the disposable workspace and its
   service identity; the canonical checkout and operator credential stores are
   denied by the operating system.
3. **Native tool bridge** — connected tools receive a Host-bound identity and
   entry-gate decision. Model arguments cannot replace actor, chat, thread, or
   workspace fields.
4. **Publish receipt** — changes return through the disposable workspace
   receipt. Unmatched deletes and host-side copies are rejected before the
   canonical checkout is touched.

The default policy is deny. A provider's own `--sandbox` or permission profile
is useful for ergonomics, but it is not the security boundary. No provider is
given `sudo`, the operator's HOME, or personal provider credentials by default.

Use `lumen agent-world certify --live` to verify the boundary with a disposable
fixture. The command reports workspace write, canonical write/delete, host
escape, secret read, sudo, `twg`, and identity checks without printing secret
values.
