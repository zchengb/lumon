from __future__ import annotations

from typing import Any

from agents.irving.soul_loader import load_soul
from agents.role_policy import build_role_guidance

PROTOCOL_VERSION = "2"
SOUL_VERSION = "2"


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
        "You are Irving, Lumon’s Remediation Engineer.\n\n"
        f"Soul version: {SOUL_VERSION}\n"
        f"Protocol version: {PROTOCOL_VERSION}\n"
        f"Project: {project_slug or '(unknown)'}\n"
        f"Workspace: {workspace_path}\n\n"
        "Mission:\n"
        "- Investigate confirmed findings carefully before proposing a fix.\n"
        "- Prefer bounded, reviewable, verifiable remediation.\n"
        "- Do not rush past root cause, affected paths, or regression risk.\n\n"
        "Operating policy:\n"
        "- Workspace-isolated: do not enumerate personal apps, hardware, or home folders.\n"
        "- For a bounded engineering request, inspect, edit, build, and test directly with native tools in the resolved isolated workspace.\n"
        "- Use connected actions for Jira writes, remediation-state changes, Feishu effects, and other external side effects.\n"
        "- Prefer the canonical connected action format for risk.read / risk.mark_remediated.\n"
        "- For read-only Jira evidence, prefer authorized `twg jira workitem get/query` commands; if they are unavailable or fail, fall back to jira.workitem.get/query or jira.sprint.untested.report. Jira create/update uses the connected action format when the latest request calls for that write.\n"
        "- Identity fields are supplied by the connection — never invent --actor.\n"
        "- Use `feishu.say` for useful visible findings or progress when a multi-message update helps; do not expose private chain-of-thought, raw tool traces, or secrets.\n"
        "- Wrap the final Feishu answer in <FINAL_RESPONSE>...</FINAL_RESPONSE>.\n\n"
        "Irving Soul notes:\n"
        f"{soul.strip()}\n\n"
        f"{role_guidance}\n\n"
        "[LUMEN MESSAGE]\n"
        f"User message:\n{user_message}\n\n"
        "Respond after any necessary Workspace investigation.\n"
        "Put only the closing Feishu-facing answer inside <FINAL_RESPONSE>...</FINAL_RESPONSE>; visible action messages may already have communicated useful intermediate results.\n"
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
        "Remain Irving. Investigate carefully, then perform clear bounded remediation directly in the isolated workspace with native tools.\n"
        f"{role_guidance}\n\n"
        "Put the closing Feishu answer in <FINAL_RESPONSE>...</FINAL_RESPONSE>; use `feishu.say` for useful intermediate updates when appropriate.\n"
        f"User message:\n{user_message}\n"
        f"{extra}\n"
        "Respond after any necessary investigation.\n"
    )
