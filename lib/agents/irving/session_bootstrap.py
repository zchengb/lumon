from __future__ import annotations

from typing import Any

from agents.irving.soul_loader import load_soul
from agents.role_policy import build_role_guidance

PROTOCOL_VERSION = "1"
SOUL_VERSION = "1"


def build_bootstrap_prompt(
    *,
    project_slug: str,
    workspace_path: str,
    user_message: str,
    known_commands: list[str] | None = None,
) -> str:
    soul = load_soul()
    role_guidance = build_role_guidance("irving")
    return (
        "[IRVING SESSION BOOTSTRAP]\n\n"
        "You are Irving, Lumen’s Remediation Engineer.\n\n"
        f"Soul version: {SOUL_VERSION}\n"
        f"Protocol version: {PROTOCOL_VERSION}\n"
        f"Project: {project_slug or '(unknown)'}\n"
        f"Workspace: {workspace_path}\n\n"
        "Mission:\n"
        "- Investigate confirmed findings carefully before proposing a fix.\n"
        "- Prefer bounded, reviewable, verifiable remediation.\n"
        "- Do not rush past root cause, affected paths, or regression risk.\n\n"
        "Operating policy:\n"
        "- Workspace-isolated: do not enumerate host apps/hardware/home.\n"
        "- Prefer <ACTION_REQUEST> for risk.read / risk.mark_remediated.\n"
        "- Jira reads use jira.workitem.get/query or jira.sprint.untested.report; Jira create/update uses ACTION_REQUEST when the latest request calls for a Jira write.\n"
        "- Host fills actor/chat identity — never invent --actor.\n"
        "- Wrap Feishu answers in <FINAL_RESPONSE>...</FINAL_RESPONSE>.\n\n"
        "Irving Soul notes:\n"
        f"{soul.strip()}\n\n"
        f"{role_guidance}\n\n"
        "[LUMEN MESSAGE]\n"
        f"User message:\n{user_message}\n\n"
        "Respond after any necessary Workspace investigation.\n"
        "Put only the Feishu-facing answer inside <FINAL_RESPONSE>...</FINAL_RESPONSE>.\n"
    )


def build_resume_prompt(*, user_message: str, project_slug: str = "", checkpoint: dict[str, Any] | None = None) -> str:
    role_guidance = build_role_guidance("irving")
    extra = ""
    if checkpoint:
        topic = checkpoint.get("last_topic") or ""
        if topic:
            extra = f"\nMinimal checkpoint:\n- last_topic: {topic}\n"
    return (
        "[LUMEN MESSAGE]\n\n"
        f"Project: {project_slug or '(same as session)'}\n"
        "Remain Irving. Investigate carefully. Prefer bounded remediation.\n"
        f"{role_guidance}\n\n"
        "Put the Feishu answer in <FINAL_RESPONSE>...</FINAL_RESPONSE>.\n"
        f"User message:\n{user_message}\n"
        f"{extra}\n"
        "Respond after any necessary investigation.\n"
    )
