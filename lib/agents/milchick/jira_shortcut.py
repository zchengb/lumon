from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Optional

from agents.milchick.jira_designer import JiraDesignUnavailable, design_jira_issue
from agents.runtime.final_response import prefer_action_summary
from agents.runtime.interaction import current_version_for_workspace
from agents.security.access_policy import classify_authorization_intent
from agents.security.broker import CapabilityBroker
from agents.security.trusted import TrustedActionContext, bind_action_request
from feishu.config import load_agents_config


_CREATE_TOKENS = (
    "create jira",
    "jira card",
    "jira ticket",
    "建卡",
    "创建jira",
    "创建 jira",
    "建立jira",
    "建立 jira",
    "創建jira",
    "創建 jira",
)
_UPDATE_TOKENS = (
    "edit jira",
    "update jira",
    "jira.workitem.update",
    "更新jira",
    "更新 jira",
)
_RETRY_TOKENS = ("retry", "re-run", "rerun", "重试", "重試", "再试", "再試", "重新创建", "重新創建", "重新建立")


def wants_jira_create(text: str) -> bool:
    lower = str(text or "").strip().lower()
    if not lower:
        return False
    if classify_authorization_intent(lower) != "mutate_explicit":
        return False
    if any(tok in lower for tok in _UPDATE_TOKENS) and not any(tok in lower for tok in ("create", "建", "创建")):
        return False
    direct = any(tok in lower for tok in _CREATE_TOKENS)
    retry = any(tok in lower for tok in _RETRY_TOKENS) and any(
        tok in lower for tok in ("jira", "workitem", "建卡")
    )
    return direct or retry


def _version_target(user_text: str, *, current_version: str) -> str:
    raw = str(user_text or "")
    explicit = re.search(r"\bv?(\d+\.\d+\.\d+)\b", raw)
    minor_requested = bool(re.search(r"\bminor\b|小版本|次版本|minor", raw.casefold()))
    if explicit and not minor_requested:
        return explicit.group(1)
    if not current_version or not minor_requested:
        return ""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?", current_version.strip())
    return f"{match.group(1)}.{int(match.group(2)) + 1}.0" if match else ""


def _anchor_blob(anchored_text: str) -> str:
    raw = str(anchored_text or "")
    marker = "Prior message content:"
    idx = raw.find(marker)
    if idx < 0:
        return ""
    body = raw[idx + len(marker) :].strip()
    if body.startswith("-----"):
        body = body[5:].lstrip()
    end = body.find("\n-----")
    if end >= 0:
        body = body[:end]
    return body.strip()


def _texts_from_card(payload: dict[str, Any]) -> tuple[str, str]:
    title = str(payload.get("title") or "").strip()
    chunks: list[str] = []
    elements = payload.get("elements")
    rows = elements if isinstance(elements, list) else []
    for row in rows:
        items = row if isinstance(row, list) else [row]
        for item in items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                chunks.append(text)
    description = "\n".join(chunks).strip()
    if title.startswith("回覆："):
        title = title[len("回覆：") :].strip()
    title = re.sub(r"^<[^>]+>\s*", "", title).strip() or title
    return title, description


def summary_and_description(*, user_text: str, anchored_text: str) -> tuple[str, str]:
    blob = _anchor_blob(anchored_text)
    summary = ""
    description = ""
    if blob:
        try:
            payload = json.loads(blob)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            summary, description = _texts_from_card(payload)
        if not summary and not description:
            description = blob[:4000]
            first = next((line.strip() for line in blob.splitlines() if line.strip()), "")
            summary = first[:120]
    if not summary:
        cleaned = re.sub(r"@_user_\d+\s*", "", str(user_text or "")).strip()
        cleaned = re.sub(r"(?i)please\s+create\s+the\s+jira\s+card\s+for\s+this\s+issue", "", cleaned).strip()
        summary = cleaned[:120] or "Feishu issue follow-up"
    if not description:
        description = str(user_text or "").strip()
    return summary[:240], description[:6000]


def _draft_issue(
    *,
    user_text: str,
    anchored_text: str,
    project_slug: str,
    workspace: Path | None,
    designer_runner=None,
) -> dict[str, Any]:
    source_title, source_body = summary_and_description(user_text=user_text, anchored_text=anchored_text)
    if workspace is None or not Path(workspace).is_dir():
        return {
            "summary": source_title,
            "description": (
                "## Problem\n"
                f"{source_body or source_title}\n\n"
                "## Source feedback\n"
                f"{source_body}"
            ).strip(),
            "issue_type": "Bug",
            "priority": "",
            "labels": [],
            "drafted": False,
        }
    try:
        designed = design_jira_issue(
            source_title=source_title,
            source_body=source_body,
            user_text=user_text,
            project_slug=project_slug,
            workspace=Path(workspace),
            runner=designer_runner,
            agents_config=load_agents_config(),
        )
        designed["drafted"] = True
        return designed
    except JiraDesignUnavailable:
        return {
            "summary": source_title,
            "description": (
                "## Problem\n"
                f"{source_body or source_title}\n\n"
                "## Source feedback\n"
                f"{source_body}\n\n"
                "_Automated Jira draft enrichment was unavailable; the source feedback was retained._"
            ).strip(),
            "issue_type": "Bug",
            "priority": "",
            "labels": [],
            "drafted": False,
        }


def try_milchick_jira_create(
    *,
    user_text: str,
    anchored_text: str,
    context: TrustedActionContext,
    workspace: Path | None = None,
    broker: CapabilityBroker | None = None,
    designer_runner=None,
) -> Optional[dict[str, Any]]:
    if str(context.agent_id or "").strip().lower() != "milchick":
        return None
    if not wants_jira_create(user_text):
        return None
    draft = _draft_issue(
        user_text=user_text,
        anchored_text=anchored_text,
        project_slug=context.project_slug,
        workspace=workspace,
        designer_runner=designer_runner,
    )
    arguments: dict[str, Any] = {
        "summary": draft["summary"],
        "description": draft["description"],
        "issue_type": draft.get("issue_type") or "Bug",
    }
    if draft.get("priority"):
        arguments["priority"] = draft["priority"]
    if draft.get("labels"):
        arguments["labels"] = draft["labels"]
    version_values = {
        "summary": draft["summary"],
        "description": draft["description"],
        "request": user_text,
    }
    current_version = current_version_for_workspace(Path(workspace), version_values) if workspace else ""
    target_version = _version_target(user_text, current_version=current_version)
    if current_version and target_version:
        arguments["target_version"] = target_version
        arguments["description"] = (
            f"{arguments['description'].rstrip()}\n\n"
            "## Version target\n"
            f"Current displayed version: {current_version}\n"
            f"Target version: {target_version} (+1 minor)."
        ).strip()
    elif current_version:
        arguments["description"] = (
            f"{arguments['description'].rstrip()}\n\n"
            f"Current displayed version read from the registered workspace: {current_version}."
        ).strip()
    request_context = replace(context, authorization_intent="mutate_explicit", explicit_authorization=True)
    request = bind_action_request(
        context=request_context,
        action="jira.workitem.create",
        arguments=arguments,
        resource={"summary": draft["summary"]},
    )
    receipt = (broker or CapabilityBroker()).execute(request)
    payload = receipt.to_dict()
    text = prefer_action_summary("", [payload]).strip()
    if receipt.status == "denied":
        text = f"Jira create was not executed: {receipt.error or receipt.error_code or 'denied'}"
    elif receipt.status != "succeeded":
        text = text or f"Jira create failed: {receipt.error or receipt.error_code or receipt.status}"
    elif not text:
        text = "Jira create finished without a key."
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    return {
        "status": "ok" if receipt.status == "succeeded" and str(result.get("status") or "") != "failed" else "error",
        "action": "jira.workitem.create",
        "text": text,
        "action_receipts": [payload],
        "final_response_mode": "host_shortcut",
        "final_response_valid": True,
        "typing": {"enabled": False},
        "flags": {
            "conversation_v4": True,
            "mode": "autonomous_workspace",
            "jira_shortcut": True,
            "jira_drafted": bool(draft.get("drafted")),
        },
        "workspace": str(workspace) if workspace else "",
    }
