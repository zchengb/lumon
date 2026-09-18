"""Tests for Langfuse telemetry and content redaction."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

import lumon.observability as observability
from lumon.agents.agent.config import AgentConfig, ObservabilityConfig
from lumon.observability import LangfuseAgentTelemetry, NoopAgentTelemetry, redact_text
from lumon.version import __version__


class FakeContext:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.entered = False
        self.exited = False

    def __enter__(self) -> Any:
        self.entered = True
        return self.value

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        del exc_type, exc_value, traceback
        self.exited = True


class FakeObservation:
    def __init__(self, name: str, as_type: str, **arguments: object) -> None:
        self.name = name
        self.as_type = as_type
        self.arguments = arguments
        self.updates: list[dict[str, object]] = []
        self.children: list[FakeObservation] = []
        self.contexts: list[FakeContext] = []

    def update(self, **arguments: object) -> None:
        self.updates.append(arguments)

    def start_as_current_observation(self, **arguments: object) -> FakeContext:
        observation_arguments = dict(arguments)
        observation_arguments.pop("name", None)
        observation_arguments.pop("as_type", None)
        child = FakeObservation(
            str(arguments["name"]),
            str(arguments.get("as_type", "span")),
            **observation_arguments,
        )
        self.children.append(child)
        context = FakeContext(child)
        self.contexts.append(context)
        return context


class FakeClient:
    def __init__(self) -> None:
        self.root: FakeObservation | None = None
        self.root_context: FakeContext | None = None
        self.shutdown_calls = 0

    def start_as_current_observation(self, **arguments: object) -> FakeContext:
        observation_arguments = dict(arguments)
        observation_arguments.pop("name", None)
        observation_arguments.pop("as_type", None)
        self.root = FakeObservation(
            str(arguments["name"]),
            str(arguments.get("as_type", "span")),
            **observation_arguments,
        )
        self.root_context = FakeContext(self.root)
        return self.root_context

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class FakePropagation:
    def __init__(self, calls: list[dict[str, object]], **arguments: object) -> None:
        self.calls = calls
        self.arguments = arguments
        self.context = FakeContext(self)

    def __enter__(self) -> FakePropagation:
        self.calls.append(self.arguments)
        self.context.entered = True
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        del exc_type, exc_value, traceback
        self.context.exited = True


def _config(*, capture_content: bool = False) -> AgentConfig:
    return AgentConfig(
        enabled=True,
        feishu_app_id="cli_test",
        feishu_app_secret="feishu-secret",
        observability=ObservabilityConfig(
            enabled=True,
            capture_content=capture_content,
        ),
    )


def _start_trace(
    client: FakeClient,
    *,
    capture_content: bool,
) -> tuple[LangfuseAgentTelemetry, observability.AgentTrace, list[dict[str, object]]]:
    propagation_calls: list[dict[str, object]] = []

    def propagate(**arguments: object) -> FakePropagation:
        return FakePropagation(propagation_calls, **arguments)

    telemetry = LangfuseAgentTelemetry(
        client,
        propagate,
        capture_content=capture_content,
        sensitive_values=("feishu-secret",),
    )
    trace = telemetry.start_trace(
        run_id="run-1",
        session_id="session-1",
        event_id="event-1",
        sender_id="sender-1",
        chat_type="p2p",
        workspace_id=uuid4(),
        provider="codex",
        model="gpt-5.6-luna",
        reasoning_effort="max",
        input_text="private request",
    )
    return telemetry, trace, propagation_calls


def test_redact_text_masks_configured_and_common_credentials() -> None:
    value = (
        'password = "feishu-secret"\n'
        "Authorization: Bearer abc.def.ghi\n"
        'OPENAI_API_KEY = "openai-secret-value"\n'
        "GITHUB_TOKEN=github-token-value\n"
        "DATABASE_URL=postgres://lumon:db-password@database.internal\n"
        "api_key=sk-123456789\n"
        "-----BEGIN PRIVATE KEY-----\nprivate material\n-----END PRIVATE KEY-----"
    )

    redacted = redact_text(value, ("feishu-secret",))

    assert "feishu-secret" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "openai-secret-value" not in redacted
    assert "github-token-value" not in redacted
    assert "db-password" not in redacted
    assert "sk-123456789" not in redacted
    assert "private material" not in redacted
    assert redacted.count("[REDACTED]") >= 4


def test_langfuse_trace_captures_redacted_content_when_legacy_toggle_is_false() -> None:
    client = FakeClient()
    telemetry, trace, propagation_calls = _start_trace(client, capture_content=False)

    async def run() -> None:
        trace.update(
            input_text='password = "feishu-secret" Authorization: Bearer abc123',
            metadata={"workspace_id": "workspace-1"},
        )
        async with trace.span("codex.exec", as_type="tool", metadata={"status": "running"}) as span:
            span.update(output_text="api_key=sk-123456789", metadata={"status": "succeeded"})
            async with span.span("codex.command", as_type="tool") as command_span:
                command_span.update(input_text="printf hello", output_text="hello")
        trace.finish(status="succeeded", final_text="secret answer")

    asyncio.run(run())
    telemetry.shutdown()

    assert client.root is not None
    assert client.root.arguments["input"] == "private request"
    root_update = client.root.updates[0]
    child_update = client.root.children[0].updates[0]
    nested_update = client.root.children[0].children[0].updates[0]
    final_update = client.root.updates[-1]
    root_metadata = root_update["metadata"]
    assert isinstance(root_metadata, dict)
    assert root_metadata["workspace_id"] == "workspace-1"
    assert child_update["metadata"] == {"status": "succeeded"}
    assert "feishu-secret" not in str(root_update["input"])
    assert "abc123" not in str(root_update["input"])
    assert "sk-123456789" not in str(child_update["output"])
    assert nested_update["input"] == "printf hello"
    assert nested_update["output"] == "hello"
    assert final_update["output"] == "secret answer"
    assert propagation_calls[0]["session_id"] == "session-1"
    assert propagation_calls[0]["user_id"] != "sender-1"
    assert client.root_context is not None and client.root_context.exited
    assert client.root.contexts[0].exited
    assert client.shutdown_calls == 1


def test_create_agent_telemetry_requires_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    telemetry = observability.create_agent_telemetry(_config())

    assert isinstance(telemetry, NoopAgentTelemetry)


def test_create_agent_telemetry_uses_credentials_saved_in_agent_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    client = FakeClient()
    constructor_arguments: dict[str, object] = {}

    class FakeLangfuse:
        def __new__(cls, **arguments: object) -> FakeClient:
            constructor_arguments.update(arguments)
            return client

    def fake_propagate(**arguments: object) -> FakePropagation:
        return FakePropagation([], **arguments)

    def fake_import(_: str) -> SimpleNamespace:
        return SimpleNamespace(
            Langfuse=FakeLangfuse,
            propagate_attributes=fake_propagate,
        )

    monkeypatch.setattr(observability.importlib, "import_module", fake_import)
    config = AgentConfig(
        enabled=True,
        feishu_app_id="cli_test",
        feishu_app_secret="feishu-secret",
        observability=ObservabilityConfig(
            enabled=True,
            public_key="pk-lf-saved",
            secret_key="sk-lf-saved",
        ),
    )

    telemetry = observability.create_agent_telemetry(config)

    assert isinstance(telemetry, LangfuseAgentTelemetry)
    assert constructor_arguments["public_key"] == "pk-lf-saved"
    assert constructor_arguments["secret_key"] == "sk-lf-saved"


def test_disabled_telemetry_does_not_import_or_initialize_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_import(name: str) -> Any:
        raise AssertionError(f"unexpected SDK import: {name}")

    monkeypatch.setattr(observability.importlib, "import_module", unexpected_import)

    config = AgentConfig(
        enabled=True,
        feishu_app_id="cli_test",
        feishu_app_secret="feishu-secret",
        observability=ObservabilityConfig(enabled=False),
    )

    telemetry = observability.create_agent_telemetry(config)

    assert isinstance(telemetry, NoopAgentTelemetry)


def test_create_agent_telemetry_passes_cloud_settings_to_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    client = FakeClient()
    constructor_arguments: dict[str, object] = {}

    class FakeLangfuse:
        def __new__(cls, **arguments: object) -> FakeClient:
            constructor_arguments.update(arguments)
            return client

    def fake_propagate(**arguments: object) -> FakePropagation:
        return FakePropagation([], **arguments)

    fake_module = SimpleNamespace(
        Langfuse=FakeLangfuse,
        propagate_attributes=fake_propagate,
    )

    def fake_import(name: str) -> SimpleNamespace:
        del name
        return fake_module

    monkeypatch.setattr(observability.importlib, "import_module", fake_import)
    config = AgentConfig(
        enabled=True,
        feishu_app_id="cli_test",
        feishu_app_secret="feishu-secret",
        observability=ObservabilityConfig(
            enabled=True,
            base_url="https://us.cloud.langfuse.com",
            capture_content=True,
            sample_rate=0.25,
        ),
    )

    telemetry = observability.create_agent_telemetry(config)

    assert isinstance(telemetry, LangfuseAgentTelemetry)
    assert constructor_arguments == {
        "public_key": "pk-lf-test",
        "secret_key": "sk-lf-test",
        "base_url": "https://us.cloud.langfuse.com",
        "sample_rate": 0.25,
        "release": __version__,
        "environment": "production",
    }


def test_create_agent_telemetry_falls_back_when_sdk_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")

    class FailingLangfuse:
        def __new__(cls, **arguments: object) -> Any:
            del cls, arguments
            raise RuntimeError("test SDK failure")

    def fake_propagate(**arguments: object) -> dict[str, object]:
        return arguments

    fake_module = SimpleNamespace(
        Langfuse=FailingLangfuse,
        propagate_attributes=fake_propagate,
    )

    def fake_import(name: str) -> SimpleNamespace:
        del name
        return fake_module

    monkeypatch.setattr(observability.importlib, "import_module", fake_import)

    telemetry = observability.create_agent_telemetry(_config())

    assert isinstance(telemetry, NoopAgentTelemetry)
