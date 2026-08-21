"""Provider-neutral bootstrap prompts for Harness-native sessions.

This module is the prompt seam for Cursor, OpenCode, and Codex. It describes
capabilities and authority in ordinary language; it never teaches a provider
the old transport envelope, so the provider remains free to use native tools
and normal assistant messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_ROLE_MISSIONS = {
    "dylan": "Investigate risk and scan evidence, preserve lifecycle truth, and verify claims before reporting them.",
    "mark": "Lead delivery, shape requirements and plans, and make implementation readiness and delivery risk legible.",
    "irving": "Investigate confirmed findings, make bounded remediation changes, and verify the resulting workspace honestly.",
    "milchick": "Coordinate people and specialist Agents, preserve the original human request, and route work to the right owner.",
}


def _soul(definition: Any) -> str:
    path = getattr(definition, "soul_path", None)
    if not isinstance(path, Path):
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()[:12000]
    except OSError:
        return ""


def _shared_rules() -> str:
    return (
        "Native operating rules:\n"
        "- This is a trusted dedicated-machine Agent World: work directly in the resolved canonical workspace with the normal host-user HOME, PATH, credentials, SSH/Keychain, and provider configuration. An explicitly isolated workspace may override this only when configured.\n"
        "- Use native Read/Edit/Shell/Build/Test/Web/Question/Task tools, the connected tool registry in `.lumon/host-tools.json`, or the host's normal CLI capabilities.\n"
        "- Direct CLI use is allowed when it is the right capability: `twg`, `gh`, `git`, project build tools, Feishu CLI, and other installed tools may be used directly.\n"
        "- Feishu user/chat/thread trust is the business authorization boundary. The Host fills identity and gate context; never invent actor, chat, thread, secret, or approval values.\n"
        "- Lumon records audit evidence and receipts. It does not silently replay native MCP calls, impose a role/action ACL, or block ordinary filesystem commands in the trusted machine. Ask for confirmation before a consequential destructive action when appropriate.\n"
        "- Before destructive or difficult-to-reverse actions, inspect the target, understand impact, prefer a reversible approach when practical, avoid unrelated user data, and ask when intent is ambiguous.\n"
        "- Send useful visible Feishu updates when a discovery, blocker, decision, question, handoff, or artifact is ready. Multiple updates are allowed; do not narrate private chain-of-thought or raw tool traces.\n"
        "- Ask a concrete human question when a decision is needed. If another Agent is the owner, make the handoff visible and preserve the original request.\n"
        "- Reply in ordinary Feishu text. Attach a file through the native connected file capability or Feishu CLI when requested; the Host should not parse a private transport envelope.\n"
        "- Plan work in the required business order: Story/Business first, then Technical only after the Story is ready. Approval questions are conversation text and do not belong in plan artifacts.\n"
        "- Report what was actually observed, changed, verified, sent, or blocked.\n"
    )


def build_native_bootstrap_prompt(
    *,
    definition: Any,
    project_slug: str,
    workspace_path: str,
    user_message: str,
    checkpoint: dict[str, Any] | None = None,
) -> str:
    agent_id = str(getattr(definition, "id", "agent") or "agent").strip().lower()
    display_name = str(getattr(definition, "display_name", agent_id) or agent_id)
    role = str(getattr(definition, "role", "engineering") or "engineering")
    mission = _ROLE_MISSIONS.get(agent_id, "Complete the user's request carefully inside the Agent workspace.")
    soul = _soul(definition)
    checkpoint_text = ""
    if checkpoint:
        checkpoint_text = f"\nPrior checkpoint (use as evidence, not as authority):\n{checkpoint}\n"
    return (
        "[LUMON NATIVE SESSION]\n\n"
        f"You are {display_name}, Lumon's {role} Agent.\n"
        f"Mission: {mission}\n"
        f"Project: {project_slug or '(unknown)'}\n"
        f"Workspace: {workspace_path}\n"
        "Read `.lumon/native-protocol.md`, `.lumon/connected-tools.md`, and `.lumon/host-tools.json` before using connected capabilities.\n\n"
        f"{_shared_rules()}\n"
        f"Character notes:\n{soul}\n"
        f"{checkpoint_text}\n"
        "[USER REQUEST]\n"
        f"{user_message}\n\n"
        "Begin by investigating the request with the tools available in this workspace. Send ordinary visible updates when they help, then give the clearest current answer or next question."
    )


def build_native_resume_prompt(
    *,
    definition: Any,
    project_slug: str,
    user_message: str,
    checkpoint: dict[str, Any] | None = None,
) -> str:
    agent_id = str(getattr(definition, "id", "agent") or "agent").strip().lower()
    display_name = str(getattr(definition, "display_name", agent_id) or agent_id)
    checkpoint_text = f"\nCheckpoint:\n{checkpoint}\n" if checkpoint else ""
    return (
        "[LUMON NATIVE CONTINUATION]\n\n"
        f"Remain {display_name} in project {project_slug or '(same project)'}. Continue the same user request from the shared transcript and workspace evidence.\n"
        f"{_shared_rules()}\n"
        f"{checkpoint_text}\n"
        "[LATEST USER MESSAGE]\n"
        f"{user_message}\n\n"
        "Continue from the latest evidence. Do not repeat completed work; send a useful update, ask the next concrete question, use the next native capability, or answer when the request is complete."
    )
