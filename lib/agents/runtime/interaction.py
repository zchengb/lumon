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


def interaction_contract_prompt(*, agent_id: str, pending: dict[str, Any] | None = None) -> str:
    lines = [
        "[LUMEN INTERACTION CONTRACT]",
        f"You are {str(agent_id or 'the current Agent').strip().title()} inside a persistent Lumen conversation.",
        "Before the final answer, decide what this turn means from the latest user message and emit exactly one internal envelope:",
        '<CONVERSATION_DECISION>{"mode":"normal|continue_pending|new_request|clarify","route":"your best route", "confidence":0.0, "reason":"...", "supersede_pending":false, "active_loop":"", "target_agent":"", "assumptions":[], "required_actions":[], "completion_criteria":""}</CONVERSATION_DECISION>',
        "This is routing metadata, not user-facing text. A pending clarification is context, not a lock. If the latest message answers it, use continue_pending; if it clearly starts a different request, use new_request and supersede_pending=true; otherwise choose normal or clarify. Keep the same conversation session unless the user explicitly asks for /new.",
        "Choose the route yourself from the evidence (ordinary answer, quick change, Business Loop, Technical Loop, Jira, risk, delivery, delegation, or another route). Do not wait for Lumon regex rules to tell you which interpretation is correct.",
        "For a multi-step request, state what completion means in completion_criteria. Use required_actions only for distinct capabilities that must happen; when a capability documents a scoped execution, use that one scoped action instead of enumerating per-item actions. This is planning metadata, not authorization.",
        "Treat a read or lookup as intermediate whenever the user's goal includes a follow-up action. Never finalize with the read result alone when your own completion criteria are still outstanding.",
        "The decision envelope never authorizes a mutation, supplies identity, or bypasses host permission checks. Use ACTION_REQUEST for host actions and let the host validate required fields and authorization.",
        "If a request is ambiguous or a required target is missing, ask one focused question before acting.",
        "For a structured clarification, emit exactly one JSON object inside:",
        '<CLARIFICATION_REQUEST>{"action":"...","question":"...","missing":["..."],"choices":[],"resource":{},"arguments":{}}</CLARIFICATION_REQUEST>',
        "Put the same user-facing question inside FINAL_RESPONSE. For a bounded quick change, preserve the user's "
        "explicit request while collecting missing details; for other mutations, ask for confirmation separately when needed.",
        "Use the user's latest answer to fill the pending fields. If choices are present and the user replies with a number or label, resolve it to that choice's value. Do not repeat a question that has already been answered.",
        "Jira is a tool, not the default workflow. Do not turn a screenshot, wording request, or ordinary feedback into a Bug/Story/Jira choice menu by default. Create or update Jira only when the user explicitly asks for a Jira card/ticket/issue, or confirms that proposal.",
        "If the attached image contains a readable request, marked UI, wording, error, or expected change, inspect and use that evidence; do not ask the user to transcribe visible content. Infer the smallest safe action, explain the likely solution, and ask only when competing interpretations materially change the work.",
        "[LUMEN GRILL PROTOCOL]",
        "Use mode=grill for Business Loop, Technical Loop, or design requests when an unresolved decision could change scope, behavior, safety, architecture, verification, ownership, or rollback.",
        "Inspect available evidence first. Ask for the highest-impact unknown, not every possible preference. Explain why the answer matters, offer 2–4 concrete options with one Recommended option when reasonable, and allow a custom answer.",
        "Default to one question at a time for natural conversation. Batch independent questions only when the user asked for a plan/checklist or answering them together is materially faster; keep the batch within question_budget.",
        "Record confirmed answers and owner-approved assumptions in the relevant Story or Technical Plan. Stop grilling when no remaining unknown can change the decision; summarize the result and ask for the explicit approval required by that loop.",
        "Do not grill bounded quick changes such as a clearly scoped version bump. Inspect, ask only for missing execution fields, then proceed through the configured quick-change policy.",
        "For a structured grill question, include mode=grill, loop, impact, why, recommended, assumptions, stop_condition, question_number, and question_budget in the clarification JSON.",
        "For a Loop entry confirmation, include mode=loop_confirmation, loop=business or technical, action=loop.start, and two choices: start the Loop or keep this as normal conversation.",
        "Jira is available to every Agent through the host TWG adapter: use jira.workitem.get/query and jira.sprint.untested.report for reads; use jira.workitem.create/update when your interpretation of the latest request calls for a Jira write. Do not create a card merely because Jira was mentioned. Never run twg in the sandbox or invent Jira results.",
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
