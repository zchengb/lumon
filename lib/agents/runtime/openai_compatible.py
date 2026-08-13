from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from agents.runtime.cursor_runtime import AgentRunResult


API_PROVIDERS = frozenset({"openai", "openai_compatible"})


def is_api_provider(provider: str) -> bool:
    return str(provider or "").strip().casefold() in API_PROVIDERS


def default_base_url(provider: str) -> str:
    return "https://api.openai.com/v1"


def default_api_key_env(provider: str) -> str:
    return "OPENAI_API_KEY"


def _load_dotenv() -> None:
    from agents.dylan.model_client import _load_lumen_dotenv

    _load_lumen_dotenv()


def _endpoint(base_url: str, provider: str) -> str:
    base = (base_url or default_base_url(provider)).rstrip("/")
    return base if base.endswith("/chat/completions") else f"{base}/chat/completions"


def _content(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(item.get("text") or "") for item in value if isinstance(item, dict))
    return str(value or "")


def chat_completion_messages(
    *,
    provider: str,
    model: str,
    messages: list[dict[str, Any]],
    timeout: int,
    base_url: str = "",
    api_key_env: str = "",
    tools: list[dict[str, Any]] | None = None,
    json_mode: bool = False,
) -> tuple[dict[str, Any], str]:
    """Call an OpenAI-compatible provider with a conversation and optional tools."""
    _load_dotenv()
    env_name = str(api_key_env or default_api_key_env(provider)).strip()
    api_key = os.environ.get(env_name, "").strip()
    if not api_key:
        raise RuntimeError(f"{provider} API key is not configured ({env_name}); add it to ~/.lumon/.env.local")
    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        _endpoint(base_url, provider),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(int(timeout or 1), 1)) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:500]
        try:
            data = json.loads(raw)
            detail = data.get("error") if isinstance(data, dict) else data
            detail = detail.get("message") if isinstance(detail, dict) else detail
        except Exception:
            detail = raw
        raise RuntimeError(f"{provider} API request failed ({exc.code}): {str(detail or 'request rejected')[:300]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"{provider} API request failed: {str(exc)[:300]}") from exc
    if not isinstance(body, dict):
        raise RuntimeError(f"{provider} API returned an invalid response")
    if body.get("error"):
        error = body["error"]
        message = error.get("message") if isinstance(error, dict) else error
        raise RuntimeError(f"{provider} API request failed: {str(message or 'request rejected')[:300]}")
    return body, str(body.get("id") or "")


def chat_completion(
    *,
    provider: str,
    model: str,
    prompt: str,
    timeout: int,
    base_url: str = "",
    api_key_env: str = "",
    json_mode: bool = False,
) -> tuple[str, str]:
    body, request_id = chat_completion_messages(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout=timeout,
        base_url=base_url,
        api_key_env=api_key_env,
        json_mode=json_mode,
    )
    choices = body.get("choices")
    first = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    text = _content(message.get("content"))
    if not text.strip():
        raise RuntimeError(f"{provider} API returned no message content")
    return text, request_id


class OpenAICompatibleAgentRuntime:
    supports_stateless = True
    supports_resume = False
    uses_isolated_env = False

    def __init__(
        self,
        *,
        provider: str = "openai_compatible",
        model: str = "gpt-4o-mini",
        base_url: str = "",
        api_key_env: str = "",
        soft_timeout_seconds: int = 90,
        hard_timeout_seconds: int = 300,
        sandbox: str = "enabled",
        force: bool = False,
        trust: bool = True,
        agent_id: str = "",
        project: str = "",
    ) -> None:
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.soft_timeout_seconds = soft_timeout_seconds
        self.hard_timeout_seconds = hard_timeout_seconds
        self.sandbox = sandbox
        self.force = force
        self.trust = trust
        self.agent_id = agent_id
        self.project = project

    def run(
        self,
        *,
        workspace: Any,
        prompt: str,
        provider_session_id: str | None = None,
        trace: Any = None,
        obs: Any = None,
    ) -> AgentRunResult:
        if self.sandbox != "enabled" or self.force:
            return AgentRunResult(text="", provider_session_id="", status="security_error", error="SANDBOX_UNAVAILABLE")
        started = time.time()
        try:
            text, request_id = chat_completion(
                provider=self.provider,
                model=self.model,
                prompt=prompt,
                timeout=self.hard_timeout_seconds,
                base_url=self.base_url,
                api_key_env=self.api_key_env,
            )
            result = AgentRunResult(
                text=text,
                provider_session_id="",
                request_id=request_id,
                duration_ms=int((time.time() - started) * 1000),
                status="succeeded",
            )
            if obs and trace:
                obs.emit(trace, "agent.result.completed", duration_ms=result.duration_ms, request_id=request_id)
            return result
        except Exception as exc:
            error = str(exc)[:500]
            if obs and trace:
                obs.emit(trace, "agent.result.failed", error=error[:300], level="ERROR")
            return AgentRunResult(
                text="",
                provider_session_id="",
                duration_ms=int((time.time() - started) * 1000),
                status="provider_error",
                error=error,
            )
