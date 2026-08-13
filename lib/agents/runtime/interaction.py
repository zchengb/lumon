from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_ACTION_REQUIREMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "loop.start": (("loop",),),
    "delivery.start": (("story", "story_id", "issue_key"),),
    "delivery.cancel": (("run_id", "story", "story_id"),),
    "delivery.quick_change": (("repository", "repo", "repository_name"), ("target_files", "target_file", "file"), ("request", "task", "change")),
    "test_case.generate": (("issue_key", "story", "story_id", "scope"),),
    "loop.business": (),
    "loop.technical": (("issue_key", "story", "story_id"),),
    "risk.resolve": (("finding_id",),),
    "risk.mark_remediated": (("finding_id",),),
    "risk.reconcile": (("project",),),
    "agent.job.create": (("target_agent",), ("capability",)),
    "agent.job.cancel": (("job_id",),),
    "agent.job.retry": (("job_id",),),
    "jira.workitem.create": (("summary",),),
    "jira.workitem.update": (("issue_key",),),
    "jira.workitem.get": (("issue_key", "id", "key"),),
    "jira.workitem.query": (("jql",),),
    "jira.sprint.untested.report": (),
}

_FIELD_LABELS = {
    "story": "Story / Jira key",
    "run_id": "delivery run ID",
    "issue_key": "Jira issue key",
    "scope": "generation scope",
    "finding_id": "finding ID",
    "project": "project",
    "target_agent": "target Agent",
    "capability": "capability",
    "job_id": "job ID",
    "summary": "Jira title",
    "loop": "Business or Technical Loop",
    "repository": "repository",
    "target_files": "target file(s)",
    "request": "requested change",
    "target_version": "target version",
}

_SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _json_safe(value: Any, *, limit: int = 2400) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item, limit=limit) for key, item in list(value.items())[:32]}
    if isinstance(value, list):
        return [_json_safe(item, limit=limit) for item in value[:32]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str):
            return value[:limit]
        return value
    return str(value)[:limit]


def _safe_text_list(value: Any, *, limit: int = 8, item_limit: int = 800) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:item_limit] for item in value[:limit] if str(item).strip()]


def version_upgrade_choices(current_version: str = "") -> list[dict[str, Any]]:
    match = _SEMVER_RE.fullmatch(str(current_version or "").strip())
    if match:
        major, minor, patch = (int(item) for item in match.groups())
        values = (
            (f"{major}.{minor}.{patch + 1}", "patch", "Smallest release change", True),
            (f"{major}.{minor + 1}.0", "minor", "Add a backward-compatible feature", False),
            (f"{major + 1}.0.0", "major", "Potentially breaking release", False),
        )
    else:
        return [
            {"value": "patch", "label": "Patch bump", "description": "Increase only the patch component", "recommended": True},
            {"value": "minor", "label": "Minor bump", "description": "Increase the minor component", "recommended": False},
            {"value": "major", "label": "Major bump", "description": "Increase the major component", "recommended": False},
        ]
    return [
        {"value": value, "label": f"{value} · {kind}", "description": description, "recommended": recommended}
        for value, kind, description, recommended in values
    ]


def _read_version_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if path.name == "package.json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {}
        if isinstance(payload, dict) and str(payload.get("version") or "").strip():
            return str(payload["version"]).strip()
    match = re.search(r"\bv?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", text)
    return match.group(0) if match else ""


def current_version_for_workspace(workspace: Path, values: dict[str, Any] | None = None) -> str:
    """Read the most relevant registered version without leaving the workspace."""
    data = values if isinstance(values, dict) else {}
    request = " ".join(
        str(data.get(key) or "")
        for key in ("summary", "description", "request", "task", "change", "change_type")
    ).casefold()
    repository = str(data.get("repository") or data.get("repo") or "").strip()
    root = Path(workspace).expanduser().resolve()
    try:
        from delivery_workspace import discover_git_repos, load_workspace_config, repo_path_for_name

        workspace_root, workspace_config = load_workspace_config(root)
        discovered = discover_git_repos(workspace_root, workspace_config)
        if not repository and "admin portal" in request and "digital-platform-admin" in discovered:
            repository = "digital-platform-admin"
        if not repository:
            repository = next(
                (
                    name
                    for name in discovered
                    if name.casefold() in request or name.casefold().replace("-", " ") in request
                ),
                "",
            )
        if repository:
            repo = repo_path_for_name(repository, workspace_root, workspace_config, discovered)
            if repo is not None:
                root = repo.resolve()
            else:
                candidate = workspace_root / "repos" / repository
                if candidate.is_dir():
                    root = candidate.resolve()
    except Exception:
        if repository:
            for candidate in (root / repository, root / "repos" / repository):
                if candidate.is_dir():
                    root = candidate.resolve()
                    break
        elif "admin portal" in request:
            candidate = root / "repos" / "digital-platform-admin"
            if candidate.is_dir():
                root = candidate.resolve()

    raw_targets = data.get("target_files") or data.get("target_file") or data.get("file") or []
    targets = [raw_targets] if isinstance(raw_targets, str) else raw_targets
    if not isinstance(targets, list):
        targets = []
    names = [str(item or "").strip() for item in targets if str(item or "").strip()]
    display_version = bool(
        re.search(r"admin portal|display|shown|bottom|left|ui|frontend|页面|左下角|版本号|版本號", request)
    )
    defaults = (
        ("public/config.js", "public/config.local.js", "public/config.dev.js", "package.json", "VERSION")
        if display_version
        else ("package.json", "VERSION", "version.txt", "pyproject.toml")
    )
    names.extend(name for name in defaults if name not in names)
    for name in names[:16]:
        candidate = (root / name).resolve()
        if root not in candidate.parents or not candidate.is_file():
            continue
        version = _read_version_file(candidate)
        if version:
            return version
    return ""


def _choice_parts(item: Any) -> tuple[str, str, str, bool]:
    if isinstance(item, dict):
        value = str(item.get("value") or item.get("target_version") or item.get("label") or "").strip()
        label = str(item.get("label") or value).strip()
        description = str(item.get("description") or "").strip()
        recommended = bool(item.get("recommended"))
        return value[:200], label[:240], description[:400], recommended
    value = str(item or "").strip()
    return value[:200], value[:240], "", False


def format_clarification_reply(question: str, choices: Any, current_version: str = "") -> str:
    text = str(question or "").strip()
    rows = choices if isinstance(choices, list) else []
    normalized = [_choice_parts(item) for item in rows[:4]]
    normalized = [item for item in normalized if item[0] and item[1]]
    if not normalized:
        return text
    if clarification_has_rendered_choices(text, rows):
        return text
    lines = []
    if str(current_version or "").strip():
        lines.extend([f"Current version: {str(current_version).strip()}", ""])
    lines.extend([text, "", "Suggested options (reply with the number or exact value):"])
    for index, (_, label, description, recommended) in enumerate(normalized, start=1):
        suffix = " — Recommended" if recommended else ""
        detail = f" — {description}" if description else ""
        lines.append(f"{index}. {label}{suffix}{detail}")
    custom_label = "custom target version" if current_version or any(_SEMVER_RE.search(value) for value, *_ in normalized) else "custom answer"
    lines.append(f"You can also reply with a {custom_label}.")
    return "\n".join(line for line in lines if line is not None).strip()


def clarification_has_rendered_choices(text: str, choices: Any) -> bool:
    """Avoid appending a second option list when the Agent already rendered it."""
    if not isinstance(choices, list) or len(choices) < 2:
        return False
    raw = str(text or "").strip()
    if not raw:
        return False
    if "suggested options" in raw.casefold():
        return True
    expected = min(2, len(choices))
    letter_rows = len(re.findall(r"(?im)^\s*(?:[-*]\s*)?\*{0,2}[A-D]\*{0,2}(?:[.)：:、-]|\s)", raw))
    numbered_rows = len(re.findall(r"(?m)^\s*(?:[-*]\s*)?\*{0,2}\d+\*{0,2}[.)：:、-]\s", raw))
    return max(letter_rows, numbered_rows) >= expected


def clarification_choice_hint(answer: str, pending: dict[str, Any] | None) -> str:
    if not isinstance(pending, dict):
        return ""
    choices = pending.get("choices") if isinstance(pending.get("choices"), list) else []
    if not choices:
        return ""
    raw = str(answer or "").strip()
    selected_index = None
    match = re.fullmatch(r"(?:option\s*)?([1-9])(?:[.)]|\s+)?", raw, re.IGNORECASE)
    if match:
        index = int(match.group(1))
        if index <= len(choices):
            selected_index = index - 1
    if selected_index is None:
        answer_key = raw.casefold()
        for index, item in enumerate(choices):
            value, label, _, _ = _choice_parts(item)
            if answer_key in {value.casefold(), label.casefold()}:
                selected_index = index
                break
    if selected_index is None:
        return ""
    value, label, _, _ = _choice_parts(choices[selected_index])
    missing = pending.get("missing") if isinstance(pending.get("missing"), list) else []
    field_key = str(missing[0] if missing else "the requested value").strip()
    field = field_key.replace("_", " ")
    if value.casefold() in {"patch", "minor", "major"}:
        resolution = (
            f"Use {value!r} as the version bump strategy for {field_key}; inspect the current version and "
            "convert it to the exact target version before emitting the action."
        )
    else:
        resolution = f"Use {value!r} as the answer for {field_key} ({field}); do not ask for that value again."
    return (
        "[LUMEN CHOICE RESOLUTION]\n"
        f"The user selected option {selected_index + 1}: {label} (value={value}). "
        f"{resolution}"
    )


def _bounded_int(value: Any, *, default: int, minimum: int = 0, maximum: int = 32) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def action_missing_fields(
    action: str,
    *,
    resource: dict[str, Any] | None = None,
    arguments: dict[str, Any] | None = None,
) -> list[str]:
    requirements = _ACTION_REQUIREMENTS.get(str(action or "").strip())
    if not requirements:
        return []
    values = {**dict(resource or {}), **dict(arguments or {})}

    def has_value(value: Any) -> bool:
        if isinstance(value, (list, tuple, set, frozenset, dict)):
            return bool(value)
        return bool(str(value or "").strip())

    missing: list[str] = []
    for alternatives in requirements:
        if not any(has_value(values.get(key)) for key in alternatives):
            missing.append(alternatives[0])
    if str(action or "").strip() == "delivery.quick_change":
        change_type = str(values.get("change_type") or "").casefold()
        request = str(values.get("request") or values.get("task") or values.get("change") or "").casefold()
        if (
            change_type in {"version", "version_bump", "upgrade_version"}
            or re.search(r"\b(version|upgrade|bump)\b|版本|升级|更新版本", request)
        ) and not has_value(values.get("target_version")):
            missing.append("target_version")
    if str(action or "").strip() == "jira.workitem.create" and "target_version" not in missing:
        request = " ".join(
            str(values.get(key) or "")
            for key in ("summary", "description", "request", "task", "change", "change_type")
        ).casefold()
        if re.search(r"\b(version|upgrade|bump)\b|版本|升级|更新版本", request) and not has_value(values.get("target_version")):
            missing.append("target_version")
    return missing


def clarification_question(action: str, missing: list[str]) -> str:
    if "target_version" in missing:
        return "Which version should I upgrade it to?"
    if str(action or "").strip() == "delivery.quick_change":
        if "target_version" in missing:
            return "Which version should I upgrade it to?"
        if "target_files" in missing:
            return "Which repository and file should I update?"
        if "repository" in missing:
            return "Which repository should I change?"
        if "request" in missing:
            return "What exactly should I change?"
    labels = [_FIELD_LABELS.get(item, item.replace("_", " ")) for item in missing]
    if len(labels) == 1:
        return f"Before I continue with `{action}`, what {labels[0]} should I use?"
    joined = ", ".join(labels[:-1]) + f" and {labels[-1]}"
    return f"Before I continue with `{action}`, please provide {joined}."


def normalize_clarification(
    payload: dict[str, Any],
    *,
    agent_id: str,
    source_message_id: str = "",
) -> dict[str, Any] | None:
    action = str(payload.get("action") or "").strip()
    question = str(payload.get("question") or payload.get("prompt") or "").strip()
    missing = [str(item).strip() for item in payload.get("missing", []) if str(item).strip()]
    if not question:
        if not action and not missing:
            return None
        question = clarification_question(action, missing)
    now = _now()
    raw_mode = str(payload.get("mode") or payload.get("interaction_mode") or "clarification").strip().lower()
    mode = raw_mode if raw_mode in {"clarification", "grill", "loop_confirmation"} else "clarification"
    raw_loop = str(payload.get("loop") or "").strip().lower()
    loop = raw_loop if raw_loop in {"business", "technical", "delivery", "quick_change", "general"} else "general"
    question_number = _bounded_int(payload.get("question_number"), default=1, minimum=1)
    question_budget = _bounded_int(payload.get("question_budget"), default=4, minimum=1)
    question_budget = max(question_number, question_budget)
    return {
        "question_id": str(payload.get("question_id") or f"q_{uuid.uuid4().hex[:16]}"),
        "agent_id": str(agent_id or "").strip().lower(),
        "action": action,
        "mode": mode,
        "loop": loop,
        "question": question[:1000],
        "missing": missing[:8],
        "choices": _json_safe(payload.get("choices") if isinstance(payload.get("choices"), list) else []),
        "impact": str(payload.get("impact") or "").strip()[:1000],
        "why": str(payload.get("why") or "").strip()[:1200],
        "recommended": str(payload.get("recommended") or "").strip()[:800],
        "assumptions": _safe_text_list(payload.get("assumptions"), limit=8),
        "stop_condition": str(payload.get("stop_condition") or "").strip()[:1000],
        "question_number": question_number,
        "question_budget": question_budget,
        "resource": _json_safe(payload.get("resource") if isinstance(payload.get("resource"), dict) else {}),
        "arguments": _json_safe(payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}),
        "source_message_id": source_message_id,
        "created_at": str(payload.get("created_at") or now.isoformat().replace("+00:00", "Z")),
        "expires_at": str(payload.get("expires_at") or (now + timedelta(days=1)).isoformat().replace("+00:00", "Z")),
    }


def normalize_conversation_decision(
    payload: dict[str, Any] | None,
    *,
    pending: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Normalize Agent-owned turn routing without granting it host authority."""
    if not isinstance(payload, dict):
        return None
    aliases = {
        "answer": "normal",
        "continue": "continue_pending",
        "new": "new_request",
        "question": "clarify",
    }
    raw_mode = str(payload.get("mode") or "").strip().lower().replace("-", "_")
    mode = aliases.get(raw_mode, raw_mode)
    if mode not in {"continue_pending", "new_request", "normal", "clarify"}:
        return None
    route = str(payload.get("route") or "normal").strip()[:120] or "normal"
    active_loop = str(payload.get("active_loop") or payload.get("loop") or "").strip().lower()
    if active_loop not in {"business", "technical"}:
        active_loop = ""
    try:
        raw_confidence = float(payload.get("confidence") or 0)
    except (TypeError, ValueError):
        raw_confidence = 0.0
    confidence = raw_confidence if 0 <= raw_confidence <= 1 else raw_confidence / 100
    confidence = max(0.0, min(confidence, 1.0))
    raw_supersede = payload.get("supersede_pending")
    explicit_supersede = (
        raw_supersede is True
        or str(raw_supersede or "").strip().casefold() in {"1", "true", "yes"}
    )
    supersede_pending = bool(pending) and (mode == "new_request" or explicit_supersede)
    return {
        "mode": mode,
        "route": route,
        "confidence": confidence,
        "reason": str(payload.get("reason") or "").strip()[:800],
        "supersede_pending": supersede_pending,
        "active_loop": active_loop,
        "target_agent": str(payload.get("target_agent") or "").strip().lower()[:40],
        "assumptions": _safe_text_list(payload.get("assumptions"), limit=8),
        "required_actions": _safe_text_list(payload.get("required_actions"), limit=8),
        "completion_criteria": str(payload.get("completion_criteria") or "").strip()[:1000],
    }


def interaction_contract_prompt(
    *,
    agent_id: str,
    pending: dict[str, Any] | None = None,
    workspace_path: Path | None = None,
) -> str:
    protocol_path = Path(__file__).resolve().parents[1] / "protocol.md"
    action_catalog_path = Path(__file__).resolve().parents[1] / "action-catalog.md"
    if workspace_path is not None:
        workspace = Path(workspace_path).expanduser().resolve()
        protocol_path = workspace / ".lumon" / "protocol.md"
        action_catalog_path = workspace / ".lumon" / "action-catalog.md"
    lines = [
        "[LUMON INTERACTION CONTRACT]",
        f"You are {str(agent_id or 'the current Agent').strip().title()} inside a persistent Lumon conversation.",
        f"READ the interaction protocol before responding: {protocol_path}",
        "It defines the envelope schemas (CONVERSATION_DECISION / ACTION_REQUEST / CLARIFICATION_REQUEST / FINAL_RESPONSE) and the Grill protocol.",
        "Non-negotiable:",
        "- Before the final answer, emit exactly one CONVERSATION_DECISION envelope.",
        "- To execute anything (Jira, jobs, delegation), emit exactly one ACTION_REQUEST envelope. Never claim work was delegated, created, or executed without the host receipt.",
        "- Put the Feishu-facing answer inside <FINAL_RESPONSE>...</FINAL_RESPONSE>.",
        "Envelope schemas:",
        '<CONVERSATION_DECISION>{"mode":"normal|continue_pending|new_request|clarify","route":"your best route", "confidence":0.0, "reason":"...", "supersede_pending":false, "active_loop":"", "target_agent":"", "assumptions":[], "required_actions":[], "completion_criteria":""}</CONVERSATION_DECISION>',
        '<ACTION_REQUEST>{"action":"...","arguments":{...},"resource":{}}</ACTION_REQUEST>',
        '<CLARIFICATION_REQUEST>{"action":"...","question":"...","missing":["..."],"choices":[],"resource":{},"arguments":{}}</CLARIFICATION_REQUEST>',
        f"If this turn needs a host action, READ the canonical action catalog before emitting ACTION_REQUEST: {action_catalog_path}",
        "Copy the action-specific arguments shape from that catalog; put model-selected fields in arguments and leave resource empty unless its recipe says otherwise.",
        "Use only the exact canonical action names and field names in that catalog; never invent, translate, or alias action names.",
        "A pending clarification is context, not a lock. If the latest message answers it, use continue_pending; if it clearly starts a different request, use new_request and supersede_pending=true.",
    ]
    if pending:
        safe = json.dumps(_json_safe(pending), ensure_ascii=False, separators=(",", ":"))
        lines.extend(
            [
                "There is an active clarification. Decide whether the latest message answers it or starts a different request; never repeat it solely because it is pending:",
                safe,
            ]
        )
    return "\n".join(lines) + "\n"
