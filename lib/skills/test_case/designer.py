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
    return str(_model_config(agents_config).get("model") or "cursor-grok-4.5-medium").strip() or "cursor-grok-4.5-medium"


def _model_config(agents_config: dict[str, Any] | None = None) -> dict[str, str]:
    data = agents_config if isinstance(agents_config, dict) else {}
    execution = data.get("execution") if isinstance(data.get("execution"), dict) else {}
    if execution.get("provider") or execution.get("model"):
        return {
            "provider": str(execution.get("provider") or execution.get("type") or "").strip().casefold(),
            "model": str(execution.get("model") or execution.get("name") or "").strip(),
            "base_url": str(execution.get("base_url") or "").strip(),
            "api_key_env": str(execution.get("api_key_env") or "").strip(),
        }
    for agent_id in ("milchick", "mark", "dylan", "irving"):
        agent = data.get(agent_id) if isinstance(data.get(agent_id), dict) else {}
        conversation = agent.get("conversation_v4") if isinstance(agent.get("conversation_v4"), dict) else {}
        provider = conversation.get("provider") if isinstance(conversation.get("provider"), dict) else {}
        if provider.get("provider") or provider.get("type") or provider.get("model"):
            return {
                "provider": str(provider.get("provider") or provider.get("type") or "").strip().casefold(),
                "model": str(provider.get("model") or provider.get("name") or "").strip(),
                "base_url": str(provider.get("base_url") or "").strip(),
                "api_key_env": str(provider.get("api_key_env") or "").strip(),
            }
    return {}


def _run_api_agent(
    prompt: str,
    *,
    provider: str,
    model: str,
    base_url: str = "",
    api_key_env: str = "",
    timeout: int = 240,
) -> str:
    from agents.runtime.openai_compatible import chat_completion

    try:
        output, _request_id = chat_completion(
            provider=provider,
            model=model,
            prompt=prompt,
            timeout=timeout,
            base_url=base_url,
            api_key_env=api_key_env,
            json_mode=True,
        )
    except Exception as exc:
        raise TestCaseDesignUnavailable(f"{provider} test-case designer failed: {str(exc)[:400]}") from exc
    if not str(output or "").strip():
        raise TestCaseDesignUnavailable(f"{provider} test-case designer returned empty output")
    return output


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
            configured = _model_config(agents_config)
            provider = str(configured.get("provider") or "").strip().casefold()
            selected_model = str(model or configured.get("model") or "").strip()
            if provider in {"deepseek", "deepseek_api", "openai", "openai_compatible"}:
                default_model = "deepseek-v4-flash" if provider in {"deepseek", "deepseek_api"} else "gpt-4o-mini"
                raw = _run_api_agent(
                    prompt,
                    provider=provider,
                    model=selected_model or default_model,
                    base_url=configured.get("base_url", ""),
                    api_key_env=configured.get("api_key_env", ""),
                )
            else:
                raw = _run_cursor_agent(
                    prompt,
                    model=selected_model or "cursor-grok-4.5-medium",
                    workspace=(Path(workspace).expanduser() if workspace else Path.home()),
                )
        data = _extract_json_object(raw)
        return drafts_from_payload(data)
    except TestCaseDesignUnavailable:
        raise
    except Exception as exc:
        raise TestCaseDesignUnavailable(str(exc)[:500]) from exc
