from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from skills.test_case.localization import normalize_case_type
from skills.test_case.models import StoryContext, TestCaseDraft
from skills.test_case.prompts import build_design_prompt

JsonRunner = Callable[[str], str]


class TestCaseDesignUnavailable(RuntimeError):
    code = "TEST_CASE_DESIGN_UNAVAILABLE"


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
    mark = data.get("mark") if isinstance(data.get("mark"), dict) else {}
    conversation = mark.get("conversation_v4") if isinstance(mark.get("conversation_v4"), dict) else {}
    provider = conversation.get("provider") if isinstance(conversation.get("provider"), dict) else {}
    return str(provider.get("model") or "cursor-grok-4.5-medium").strip() or "cursor-grok-4.5-medium"


def _run_cursor_agent(prompt: str, *, model: str, workspace: Path, timeout: int = 240) -> str:
    _load_lumen_dotenv()
    agent_bin = shutil.which("agent") or shutil.which("cursor-agent")
    if not agent_bin:
        raise TestCaseDesignUnavailable("cursor agent CLI not found")
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
            env=build_agent_env(agent_id="mark"),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TestCaseDesignUnavailable(f"cursor agent timed out after {timeout}s") from exc
    except Exception as exc:
        raise TestCaseDesignUnavailable(str(exc)[:400]) from exc
    output = (completed.stdout or "").strip() or (completed.stderr or "").strip()
    if completed.returncode != 0 and not output:
        raise TestCaseDesignUnavailable(f"cursor agent failed with code {completed.returncode}")
    if not output:
        raise TestCaseDesignUnavailable("cursor agent returned empty output")
    return output


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def drafts_from_payload(data: dict[str, Any]) -> list[TestCaseDraft]:
    rows = data.get("test_cases")
    if not isinstance(rows, list):
        raise ValueError("test_cases missing")
    drafts: list[TestCaseDraft] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        case_type = normalize_case_type(str(item.get("case_type") or ""))
        drafts.append(
            TestCaseDraft(
                ac_refs=_as_str_list(item.get("ac_refs")),
                title=str(item.get("title") or "").strip(),
                preconditions=_as_str_list(item.get("preconditions")),
                steps=_as_str_list(item.get("steps")),
                expected_results=_as_str_list(item.get("expected_results") or item.get("expected_result")),
                case_type=case_type or str(item.get("case_type") or "").strip().lower(),
                rationale=str(item.get("rationale") or "").strip(),
            )
        )
    if not drafts:
        raise ValueError("no test cases in model output")
    return drafts


def design_test_cases(
    story: StoryContext,
    *,
    workspace_context: dict[str, Any] | None = None,
    language: str = "zh-Hant",
    model: str | None = None,
    workspace: Path | None = None,
    runner: JsonRunner | None = None,
    agents_config: dict[str, Any] | None = None,
) -> list[TestCaseDraft]:
    prompt = build_design_prompt(story, workspace_context=workspace_context, language=language)
    try:
        if runner is not None:
            raw = runner(prompt)
        else:
            raw = _run_cursor_agent(
                prompt,
                model=str(model or _default_model_name(agents_config)).strip(),
                workspace=(Path(workspace).expanduser() if workspace else Path.home()),
            )
        data = _extract_json_object(raw)
        return drafts_from_payload(data)
    except TestCaseDesignUnavailable:
        raise
    except Exception as exc:
        raise TestCaseDesignUnavailable(str(exc)[:500]) from exc
