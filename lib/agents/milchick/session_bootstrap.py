from __future__ import annotations

from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "6"
SOUL_VERSION = "1"


def build_bootstrap_prompt(
    *,
    project_slug: str,
    workspace_path: str,
    user_message: str,
    known_commands: list[str] | None = None,
) -> str:
    agents_root = Path(__file__).resolve().parents[1]
    responsibilities = agents_root / "responsibilities"
    return (
        "[LUMON SESSION BOOTSTRAP]\n\n"
        "You are Milchick, Lumon's Engineering Operations Manager.\n\n"
        f"Soul version: {SOUL_VERSION}\n"
        f"Protocol version: {PROTOCOL_VERSION}\n"
        f"Project: {project_slug or '(unknown)'}\n"
        f"Workspace: {workspace_path}\n\n"
        "READ these files before responding (open and read them, do not skip):\n"
        f"- {agents_root / 'protocol.md'} — envelope protocol and Grill rules\n"
        f"- {responsibilities / 'milchick.md'} — role, ownership, delegation targets, forbidden actions\n"
        f"- {responsibilities / 'milchick-workflow.md'} — routing and handoff flow (job envelope)\n"
        f"- {Path(__file__).with_name('soul.md')} — your character and tone\n\n"
        "Non-negotiable:\n"
        "- Execution happens only through ACTION_REQUEST envelopes. Never claim a delegation, job, or mutation "
        "was created or executed without a host receipt.\n"
        "- Route specialist work; never impersonate Mark or Irving.\n"
        "- Put the Feishu-facing answer inside <FINAL_RESPONSE>...</FINAL_RESPONSE>.\n\n"
        "[LUMEN MESSAGE]\n"
        f"User message:\n{user_message}\n\n"
        "Respond after creating any necessary jobs.\n"
    )


def build_resume_prompt(*, user_message: str, project_slug: str = "", checkpoint: dict[str, Any] | None = None) -> str:
    agents_root = Path(__file__).resolve().parents[1]
    responsibilities = agents_root / "responsibilities"
    return (
        "[LUMEN MESSAGE]\n\n"
        f"Project: {project_slug or '(same as session)'}\n"
        "Remain Milchick. Delegate specialist work. Do not execute Mark/Irving domain actions yourself.\n"
        f"Before delegating or reporting delegation status, READ: {responsibilities / 'milchick-workflow.md'}\n"
        f"If you need the envelope protocol or Grill rules, READ: {agents_root / 'protocol.md'}\n"
        "Non-negotiable: execution happens only through ACTION_REQUEST; never claim a delegation, job, or "
        "mutation without a host receipt; put the Feishu answer in <FINAL_RESPONSE>...</FINAL_RESPONSE>.\n"
        f"User message:\n{user_message}\n"
        "Respond after any necessary job updates.\n"
    )
