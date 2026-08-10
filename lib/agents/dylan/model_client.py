from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agents.dylan.schemas import AgentPlan, AgentTask, ModelConfig, RouterResult, ToolCall


@dataclass
class GeneratedResponse:
    text: str
    mode: str = "model"
    raw: str = ""


class DylanModelClient:
    provider_name = "base"

    def classify(self, request: dict[str, Any]) -> RouterResult:
        raise NotImplementedError

    def plan(self, request: dict[str, Any]) -> AgentPlan:
        raise NotImplementedError

    def respond(self, request: dict[str, Any]) -> GeneratedResponse:
        raise NotImplementedError


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty model output")
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


def _parse_tool_calls(raw: Any) -> list[ToolCall]:
    tool_calls = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        args = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        if name:
            tool_calls.append(ToolCall(name=name, arguments=args))
    return tool_calls


def _parse_router_result(data: dict[str, Any], *, source: str) -> RouterResult:
    return RouterResult(
        intent=str(data.get("intent") or "unsupported"),
        confidence=float(data.get("confidence") or 0.0),
        source=source,
        project_slug=(str(data.get("project_slug")).strip() if data.get("project_slug") else None),
        finding_id=(str(data.get("finding_id")).strip() if data.get("finding_id") else None),
        run_id=(str(data.get("run_id")).strip() if data.get("run_id") else None),
        reference=data.get("reference") if isinstance(data.get("reference"), dict) else None,
        needs_clarification=bool(data.get("needs_clarification")),
        clarification_question=(str(data.get("clarification_question")) if data.get("clarification_question") else None),
        tool_calls=_parse_tool_calls(data.get("tool_calls")),
        params={
            "project": data.get("project_slug"),
            "finding_id": data.get("finding_id"),
            "run_id": data.get("run_id"),
            "other_agent": (data.get("params") or {}).get("other_agent") if isinstance(data.get("params"), dict) else None,
        },
    )


def _parse_agent_plan(data: dict[str, Any], *, source: str) -> AgentPlan:
    tasks: list[AgentTask] = []
    raw_tasks = data.get("tasks")
    if isinstance(raw_tasks, list) and raw_tasks:
        for idx, item in enumerate(raw_tasks):
            if not isinstance(item, dict):
                continue
            intent = str(item.get("intent") or "").strip()
            if not intent:
                continue
            tasks.append(
                AgentTask(
                    task_id=str(item.get("task_id") or f"task_{idx + 1}"),
                    intent=intent,
                    tool_calls=_parse_tool_calls(item.get("tool_calls")),
                    project_slug=(str(item.get("project_slug")).strip() if item.get("project_slug") else None),
                    finding_id=(str(item.get("finding_id")).strip() if item.get("finding_id") else None),
                    params=item.get("params") if isinstance(item.get("params"), dict) else {},
                )
            )
    elif data.get("intent"):
        tasks.append(
            AgentTask(
                task_id="task_1",
                intent=str(data.get("intent")),
                tool_calls=_parse_tool_calls(data.get("tool_calls")),
                project_slug=(str(data.get("project_slug")).strip() if data.get("project_slug") else None),
                finding_id=(str(data.get("finding_id")).strip() if data.get("finding_id") else None),
                params=data.get("params") if isinstance(data.get("params"), dict) else {},
            )
        )
    return AgentPlan(
        language=str(data.get("language") or "en"),
        confidence=float(data.get("confidence") or 0.0),
        needs_clarification=bool(data.get("needs_clarification")),
        clarification_question=(str(data.get("clarification_question")) if data.get("clarification_question") else None),
        tasks=tasks,
        source=source,
    )


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
            if not key:
                continue
            if key == "CURSOR_API_KEY" and value:
                os.environ[key] = value
            elif key not in os.environ:
                os.environ[key] = value


def _format_agent_error(exc: BaseException, *, timeout: int) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"agent timed out after {timeout}s"
    text = str(exc).strip()
    if text.startswith("Command '['"):
        return f"agent command failed/timed out after {timeout}s"
    return text[:400]


class CursorDylanModelClient(DylanModelClient):
    provider_name = "cursor"

    def __init__(self, config: Optional[ModelConfig] = None, workspace: Optional[Path] = None) -> None:
        self.config = config or ModelConfig()
        self.workspace = Path(workspace).expanduser() if workspace else Path.home()

    def _env(self) -> dict[str, str]:
        from agents.security.env import build_agent_env

        _load_lumen_dotenv()
        return build_agent_env(agent_id="dylan")

    def _run_agent(self, prompt: str, *, timeout: int) -> str:
        agent_bin = shutil.which("agent")
        if not agent_bin:
            raise RuntimeError("cursor agent CLI not found")
        args = [
            agent_bin,
            "--workspace",
            str(self.workspace),
            "--sandbox",
            "enabled",
            "--trust",
            "-p",
            "--output-format",
            "text",
            "--model",
            self.config.model_name,
            prompt,
        ]
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                env=self._env(),
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(_format_agent_error(exc, timeout=timeout)) from exc
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "agent failed")[:500])
        return completed.stdout or ""

    def classify(self, request: dict[str, Any]) -> RouterResult:
        from agents.dylan.model_prompts import router_prompt

        prompt = router_prompt(request)
        attempts = max(self.config.max_router_retries, 0) + 1
        last_error = ""
        for _ in range(attempts):
            try:
                output = self._run_agent(prompt, timeout=self.config.router_timeout_seconds)
                data = _extract_json_object(output)
                return _parse_router_result(data, source="llm:cursor")
            except Exception as exc:
                last_error = _format_agent_error(exc, timeout=self.config.router_timeout_seconds)
        raise RuntimeError(f"router model failed: {last_error}")

    def plan(self, request: dict[str, Any]) -> AgentPlan:
        from agents.dylan.model_prompts import planner_prompt

        prompt = planner_prompt(request)
        attempts = max(self.config.max_router_retries, 0) + 1
        last_error = ""
        timeout = self.config.planner_timeout_seconds or self.config.router_timeout_seconds
        for _ in range(attempts):
            try:
                output = self._run_agent(prompt, timeout=timeout)
                data = _extract_json_object(output)
                return _parse_agent_plan(data, source="llm:cursor")
            except Exception as exc:
                last_error = _format_agent_error(exc, timeout=timeout)
        raise RuntimeError(f"planner model failed: {last_error}")

    def respond(self, request: dict[str, Any]) -> GeneratedResponse:
        from agents.dylan.model_prompts import response_prompt

        prompt = response_prompt(request)
        attempts = max(self.config.max_response_retries, 0) + 1
        last_error = ""
        timeout = self.config.responder_timeout_seconds or self.config.response_timeout_seconds
        for _ in range(attempts):
            try:
                output = self._run_agent(prompt, timeout=timeout)
                data = _extract_json_object(output)
                text = str(data.get("text") or "").strip()
                if not text:
                    text = output.strip()
                return GeneratedResponse(text=text, mode="model", raw=output)
            except Exception as exc:
                last_error = _format_agent_error(exc, timeout=timeout)
                try:
                    output = self._run_agent(prompt, timeout=timeout)
                    text = output.strip()
                    if text:
                        return GeneratedResponse(text=text, mode="model_text", raw=output)
                except Exception as exc2:
                    last_error = _format_agent_error(exc2, timeout=timeout)
        raise RuntimeError(f"response model failed: {last_error}")


class HeuristicDylanModelClient(DylanModelClient):
    provider_name = "heuristic"

    def classify(self, request: dict[str, Any]) -> RouterResult:
        from agents.dylan.semantic_router import heuristic_classify

        return heuristic_classify(request)

    def plan(self, request: dict[str, Any]) -> AgentPlan:
        router = self.classify(request)
        return AgentPlan(
            language=str(request.get("language") or "en"),
            confidence=router.confidence,
            needs_clarification=router.needs_clarification,
            clarification_question=router.clarification_question,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    intent=router.intent,
                    tool_calls=router.tool_calls,
                    project_slug=router.project_slug,
                    finding_id=router.finding_id,
                    params=router.params,
                )
            ],
            source="heuristic",
        )

    def respond(self, request: dict[str, Any]) -> GeneratedResponse:
        raise RuntimeError("heuristic client does not generate freeform responses")


class FakeDylanModelClient(DylanModelClient):
    provider_name = "fake"

    def __init__(
        self,
        plan: Optional[AgentPlan] = None,
        response_text: str = "Fake agent response grounded in tool facts.",
    ) -> None:
        self._plan = plan
        self._response_text = response_text

    def classify(self, request: dict[str, Any]) -> RouterResult:
        plan = self.plan(request)
        task = plan.tasks[0] if plan.tasks else None
        return RouterResult(
            intent=task.intent if task else "unsupported",
            confidence=plan.confidence,
            source="fake",
            project_slug=task.project_slug if task else None,
            finding_id=task.finding_id if task else None,
            needs_clarification=plan.needs_clarification,
            clarification_question=plan.clarification_question,
            tool_calls=task.tool_calls if task else [],
            params=task.params if task else {},
        )

    def plan(self, request: dict[str, Any]) -> AgentPlan:
        if self._plan is not None:
            return self._plan
        message = str(request.get("message") or "").lower()
        language = str(request.get("language") or "en")
        known = request.get("known_projects") or []
        project = known[0] if isinstance(known, list) and known else None
        tasks: list[AgentTask] = []
        if any(tok in message for tok in ("mark", "milchick", "irving", "friend", "关系", "關係")):
            tasks.append(
                AgentTask(
                    task_id=f"task_{len(tasks) + 1}",
                    intent="conversation.agent_relationship",
                    tool_calls=[ToolCall(name="get_agent_relationship", arguments={"agent_id": "dylan", "other_id": "mark"})],
                )
            )
        if any(tok in message for tok in ("unresolved", "open", "finding", "未解决", "未解決", "风险", "風險", "risk")):
            tasks.append(
                AgentTask(
                    task_id=f"task_{len(tasks) + 1}",
                    intent="risk.unresolved",
                    tool_calls=[
                        ToolCall(
                            name="query_unresolved_findings",
                            arguments={"project_slug": project or "", "limit": 10},
                        )
                    ],
                    project_slug=project,
                )
            )
        if any(tok in message for tok in ("who are you", "你是谁", "你是誰", "identity")):
            tasks.append(
                AgentTask(
                    task_id=f"task_{len(tasks) + 1}",
                    intent="conversation.agent_identity",
                    tool_calls=[
                        ToolCall(name="get_agent_profile", arguments={"agent_id": "dylan"}),
                        ToolCall(name="list_agent_capabilities", arguments={"agent_id": "dylan"}),
                    ],
                )
            )
        if any(tok in message for tok in ("hi", "hello", "你好", "hey")) and not tasks:
            tasks.append(
                AgentTask(
                    task_id="task_1",
                    intent="conversation.greeting",
                    tool_calls=[ToolCall(name="get_agent_profile", arguments={"agent_id": "dylan"})],
                )
            )
        if any(tok in message for tok in ("scan", "扫描", "掃描")):
            tasks.append(
                AgentTask(
                    task_id=f"task_{len(tasks) + 1}",
                    intent="scan.run",
                    tool_calls=[],
                    project_slug=project,
                    params={"project": project, "window_days": 7},
                )
            )
        if not tasks:
            tasks.append(
                AgentTask(
                    task_id="task_1",
                    intent="conversation.small_talk",
                    tool_calls=[ToolCall(name="get_agent_profile", arguments={"agent_id": "dylan"})],
                )
            )
        return AgentPlan(language=language, confidence=0.95, tasks=tasks, source="fake")

    def respond(self, request: dict[str, Any]) -> GeneratedResponse:
        return GeneratedResponse(text=self._response_text, mode="fake")


def get_model_client(
    flags_model: ModelConfig,
    *,
    workspace: Optional[Path] = None,
    prefer_heuristic: bool = False,
    require_real: bool = False,
) -> DylanModelClient:
    if flags_model.provider == "fake":
        return FakeDylanModelClient()
    if prefer_heuristic or flags_model.provider == "heuristic":
        if require_real:
            raise RuntimeError("Agent CLI/model unavailable (heuristic blocked)")
        return HeuristicDylanModelClient()
    if flags_model.provider == "cursor" and shutil.which("agent"):
        return CursorDylanModelClient(flags_model, workspace=workspace)
    if require_real:
        raise RuntimeError("Agent CLI/model unavailable")
    return HeuristicDylanModelClient()
