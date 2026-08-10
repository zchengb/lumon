from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

JsonRunner = Callable[[str], str]


class JiraDesignUnavailable(RuntimeError):
    code = "JIRA_DESIGN_UNAVAILABLE"


def _load_lumen_dotenv() -> None:
    homes = []
    override = os.environ.get("LUMEN_HOME", "").strip()
    if override:
        homes.append(Path(override).expanduser())
    homes.append(Path.home() / ".lumon")
    seen: set[Path] = set()
    for home in homes:
        path = home / ".env.local"
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
            if key == "CURSOR_API_KEY" and value:
                os.environ[key] = value


def _default_model_name(agents_config: dict[str, Any] | None = None) -> str:
    data = agents_config if isinstance(agents_config, dict) else {}
    milchick = data.get("milchick") if isinstance(data.get("milchick"), dict) else {}
    conversation = milchick.get("conversation_v4") if isinstance(milchick.get("conversation_v4"), dict) else {}
    provider = conversation.get("provider") if isinstance(conversation.get("provider"), dict) else {}
    model = str(provider.get("model") or "").strip()
    if model:
        return model
    mark = data.get("mark") if isinstance(data.get("mark"), dict) else {}
    conversation = mark.get("conversation_v4") if isinstance(mark.get("conversation_v4"), dict) else {}
    provider = conversation.get("provider") if isinstance(conversation.get("provider"), dict) else {}
    return str(provider.get("model") or "cursor-grok-4.5-medium").strip() or "cursor-grok-4.5-medium"


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty model output")
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("no json object in model output")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("json root is not object")
    return data


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def build_design_prompt(*, source_title: str, source_body: str, user_text: str, project_slug: str) -> str:
    return (
        "You are drafting a Jira work item for the mbpass / Lumen engineering workspace.\n"
        "Investigate the workspace (repos, docs, stories, related UI/admin code) before writing.\n"
        "Do NOT paste the raw email as the description.\n"
        "Turn the feedback into a clear engineering ticket with product/context from this workspace.\n\n"
        f"Project slug: {project_slug or 'mbpass'}\n\n"
        "Source feedback title:\n"
        f"{source_title}\n\n"
        "Source feedback body:\n"
        f"{source_body}\n\n"
        "User request:\n"
        f"{user_text}\n\n"
        "Return ONLY one JSON object with keys:\n"
        "{\n"
        '  "summary": "short actionable title",\n'
        '  "issue_type": "Bug|Task|Story",\n'
        '  "priority": "Highest|High|Medium|Low|Lowest|",\n'
        '  "labels": ["optional","labels"],\n'
        '  "problem": "what is wrong / what was requested",\n'
        '  "expected": "expected behavior",\n'
        '  "actual": "actual behavior",\n'
        '  "steps_to_reproduce": ["step 1", "step 2"],\n'
        '  "acceptance_criteria": ["ac 1", "ac 2"],\n'
        '  "workspace_findings": ["relevant files/modules/behaviors found in workspace"],\n'
        '  "suggested_fix": "optional engineering note"\n'
        "}\n"
        "Write summary/description fields in the same language as the source feedback when possible.\n"
        "Prefer concrete workspace findings over restating the email.\n"
    )


def format_issue_description(draft: dict[str, Any], *, source_title: str, source_body: str) -> str:
    problem = str(draft.get("problem") or "").strip()
    expected = str(draft.get("expected") or "").strip()
    actual = str(draft.get("actual") or "").strip()
    steps = _as_str_list(draft.get("steps_to_reproduce"))
    ac = _as_str_list(draft.get("acceptance_criteria"))
    findings = _as_str_list(draft.get("workspace_findings"))
    suggested = str(draft.get("suggested_fix") or "").strip()
    lines: list[str] = []
    if problem:
        lines.extend(["## Problem", problem, ""])
    if expected:
        lines.extend(["## Expected", expected, ""])
    if actual:
        lines.extend(["## Actual", actual, ""])
    if steps:
        lines.append("## Steps to reproduce")
        lines.extend(f"{idx}. {step}" for idx, step in enumerate(steps, 1))
        lines.append("")
    if findings:
        lines.append("## Workspace findings")
        lines.extend(f"- {item}" for item in findings)
        lines.append("")
    if ac:
        lines.append("## Acceptance criteria")
        lines.extend(f"- {item}" for item in ac)
        lines.append("")
    if suggested:
        lines.extend(["## Suggested fix", suggested, ""])
    lines.extend(
        [
            "## Source feedback",
            f"**Title:** {source_title}" if source_title else "",
            source_body.strip() if source_body else "",
        ]
    )
    return "\n".join(line for line in lines if line is not None).strip()


def _run_cursor_agent(prompt: str, *, model: str, workspace: Path, timeout: int = 240) -> str:
    _load_lumen_dotenv()
    agent_bin = shutil.which("agent") or shutil.which("cursor-agent")
    if not agent_bin:
        raise JiraDesignUnavailable("cursor agent CLI not found")
    from agents.security.env import build_agent_env

    args = [
        agent_bin,
        "--workspace",
        str(workspace),
        "--trust",
        "-p",
        "--mode",
        "ask",
        "--output-format",
        "text",
        "--model",
        model,
        prompt,
    ]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=build_agent_env(agent_id="milchick"),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise JiraDesignUnavailable(f"cursor agent timed out after {timeout}s") from exc
    except Exception as exc:
        raise JiraDesignUnavailable(str(exc)[:400]) from exc
    output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
    if completed.returncode != 0 and not output:
        raise JiraDesignUnavailable(f"cursor agent failed with code {completed.returncode}")
    if not output:
        raise JiraDesignUnavailable("cursor agent returned empty output")
    return output


def design_jira_issue(
    *,
    source_title: str,
    source_body: str,
    user_text: str,
    project_slug: str,
    workspace: Path,
    model: str | None = None,
    runner: JsonRunner | None = None,
    agents_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt = build_design_prompt(
        source_title=source_title,
        source_body=source_body,
        user_text=user_text,
        project_slug=project_slug,
    )
    try:
        if runner is not None:
            raw = runner(prompt)
        else:
            raw = _run_cursor_agent(
                prompt,
                model=str(model or _default_model_name(agents_config)).strip(),
                workspace=Path(workspace).expanduser().resolve(),
            )
        data = _extract_json_object(raw)
    except JiraDesignUnavailable:
        raise
    except Exception as exc:
        raise JiraDesignUnavailable(str(exc)[:400]) from exc
    summary = str(data.get("summary") or source_title or "").strip()
    if not summary:
        raise JiraDesignUnavailable("designer returned empty summary")
    issue_type = str(data.get("issue_type") or "Bug").strip() or "Bug"
    priority = str(data.get("priority") or "").strip()
    labels = _as_str_list(data.get("labels"))
    description = format_issue_description(data, source_title=source_title, source_body=source_body)
    return {
        "summary": summary[:240],
        "description": description[:12000],
        "issue_type": issue_type,
        "priority": priority,
        "labels": labels,
        "draft": data,
    }
