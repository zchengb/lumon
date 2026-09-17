"""Provider-neutral telemetry for Lumon Agent runs."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import logging
import os
import re
from collections.abc import AsyncGenerator, Iterable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, Literal, Protocol
from uuid import UUID

from lumon.agents.agent.config import AgentConfig
from lumon.version import __version__

logger = logging.getLogger(__name__)

TelemetryLevel = Literal["DEBUG", "DEFAULT", "WARNING", "ERROR"]
TelemetryStatus = Literal[
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "interrupted",
]
ObservationType = Literal["span", "tool", "chain"]
MetadataValue = str | int | float | bool
TelemetryMetadata = Mapping[str, MetadataValue]


class TraceSpan(Protocol):
    """The safe update surface exposed to the Agent service."""

    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        """Add safe metadata and optionally redacted content to an observation."""

        ...


class AgentTrace(Protocol):
    """A trace handle for one accepted Agent message."""

    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        """Update the root trace safely."""

        ...

    def finish(
        self,
        *,
        status: TelemetryStatus,
        error_code: str | None = None,
        final_text: str | None = None,
    ) -> None:
        """Close the root trace with a safe outcome."""

        ...

    def span(
        self,
        name: str,
        *,
        as_type: ObservationType = "span",
        metadata: TelemetryMetadata | None = None,
    ) -> AbstractAsyncContextManager[TraceSpan]:
        """Create a child observation around an asynchronous operation."""

        ...


class AgentTelemetry(Protocol):
    """The telemetry dependency used by the Agent orchestration layer."""

    def start_trace(
        self,
        *,
        run_id: str,
        session_id: str,
        event_id: str,
        sender_id: str,
        chat_type: str,
        workspace_id: UUID | None,
        provider: str,
        model: str,
        reasoning_effort: str,
        input_text: str,
    ) -> AgentTrace:
        """Start one trace without coupling the service to the provider."""

        ...

    def shutdown(self) -> None:
        """Flush and stop any background exporter resources."""

        ...


class NoopAgentTelemetry:
    """Disabled telemetry that keeps the Agent path side-effect free."""

    def start_trace(
        self,
        *,
        run_id: str,
        session_id: str,
        event_id: str,
        sender_id: str,
        chat_type: str,
        workspace_id: UUID | None,
        provider: str,
        model: str,
        reasoning_effort: str,
        input_text: str,
    ) -> AgentTrace:
        del (
            run_id,
            session_id,
            event_id,
            sender_id,
            chat_type,
            workspace_id,
            provider,
            model,
            reasoning_effort,
            input_text,
        )
        return _NoopTrace()

    def shutdown(self) -> None:
        """Leave the disabled telemetry path unchanged."""


class _NoopTrace:
    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        del input_text, output_text, metadata, level, status_message

    def finish(
        self,
        *,
        status: TelemetryStatus,
        error_code: str | None = None,
        final_text: str | None = None,
    ) -> None:
        del status, error_code, final_text

    @asynccontextmanager
    async def span(
        self,
        name: str,
        *,
        as_type: ObservationType = "span",
        metadata: TelemetryMetadata | None = None,
    ) -> AsyncGenerator[TraceSpan, None]:
        del name, as_type, metadata
        yield _NoopSpan()


class _NoopSpan:
    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        del input_text, output_text, metadata, level, status_message


class LangfuseAgentTelemetry:
    """Adapt the Langfuse SDK to the provider-neutral telemetry seam."""

    def __init__(
        self,
        client: Any,
        propagate_attributes: Any,
        *,
        capture_content: bool,
        sensitive_values: Iterable[str] = (),
    ) -> None:
        # Load the SDK dynamically so a damaged installation remains fail-soft.
        # ``Any`` is confined to this third-party adapter boundary.
        # Keep the argument for compatibility with callers from the opt-in pilot;
        # content capture is now always enabled by the configuration policy.
        del capture_content
        self._client = client
        self._propagate_attributes = propagate_attributes
        self._redactor = _TextRedactor(sensitive_values)
        self._closed = False

    def start_trace(
        self,
        *,
        run_id: str,
        session_id: str,
        event_id: str,
        sender_id: str,
        chat_type: str,
        workspace_id: UUID | None,
        provider: str,
        model: str,
        reasoning_effort: str,
        input_text: str,
    ) -> AgentTrace:
        root_manager: Any | None = None
        propagation_manager: Any | None = None
        try:
            metadata = _run_metadata(
                run_id=run_id,
                event_id=event_id,
                chat_type=chat_type,
                workspace_id=workspace_id,
                provider=provider,
                model=model,
                reasoning_effort=reasoning_effort,
            )
            root_manager = self._client.start_as_current_observation(
                name="agent.turn",
                as_type="agent",
                input=self._redactor.content(input_text),
                metadata=metadata,
                version=__version__,
            )
            if root_manager is None:
                raise RuntimeError("Langfuse root observation was not created.")
            root_observation = root_manager.__enter__()
            propagation_manager = self._propagate_attributes(
                user_id=_user_reference(sender_id),
                session_id=session_id,
                metadata={
                    "lumon_run_id": _bounded(run_id),
                    "lumon_event_id": _bounded(event_id),
                },
                version=__version__,
                tags=["lumon", "agent", "feishu"],
                trace_name="agent.turn",
                environment="production",
            )
            if propagation_manager is None:
                raise RuntimeError("Langfuse propagation context was not created.")
            propagation_manager.__enter__()
            return _LangfuseTrace(
                root_manager=root_manager,
                propagation_manager=propagation_manager,
                root_observation=root_observation,
                redactor=self._redactor,
                metadata=metadata,
            )
        except Exception as exc:
            _safe_exit(propagation_manager)
            _safe_exit(root_manager)
            _log_sdk_failure("start trace", exc)
            return _NoopTrace()

    def shutdown(self) -> None:
        """Flush the SDK queue without allowing exporter errors to escape."""

        if self._closed:
            return
        self._closed = True
        try:
            self._client.shutdown()
        except Exception as exc:
            _log_sdk_failure("shutdown", exc)


class _LangfuseTrace:
    def __init__(
        self,
        *,
        root_manager: Any,
        propagation_manager: Any,
        root_observation: Any,
        redactor: _TextRedactor,
        metadata: TelemetryMetadata,
    ) -> None:
        self._root_manager = root_manager
        self._propagation_manager = propagation_manager
        self._root = _LangfuseObservation(root_observation, redactor, metadata=metadata)
        self._closed = False

    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        if self._closed:
            return
        self._root.update(
            input_text=input_text,
            output_text=output_text,
            metadata=metadata,
            level=level,
            status_message=status_message,
        )

    def finish(
        self,
        *,
        status: TelemetryStatus,
        error_code: str | None = None,
        final_text: str | None = None,
    ) -> None:
        if self._closed:
            return
        level: TelemetryLevel = "DEFAULT"
        if status in {"failed", "timed_out"}:
            level = "ERROR"
        elif status in {"cancelled", "interrupted"}:
            level = "WARNING"
        metadata: dict[str, MetadataValue] = {"status": status}
        if error_code:
            metadata["error_code"] = error_code
        self._root.update(
            output_text=final_text,
            metadata=metadata,
            level=level,
            status_message=error_code,
        )
        self._close()

    @asynccontextmanager
    async def span(
        self,
        name: str,
        *,
        as_type: ObservationType = "span",
        metadata: TelemetryMetadata | None = None,
    ) -> AsyncGenerator[TraceSpan, None]:
        manager: Any | None = None
        try:
            child_metadata = _metadata_dict(metadata)
            manager = self._root.start_as_current_observation(
                name=name,
                as_type=as_type,
                metadata=child_metadata,
            )
            if manager is None:
                raise RuntimeError("Langfuse child observation was not created.")
            observation = manager.__enter__()
        except Exception as exc:
            _safe_exit(manager)
            _log_sdk_failure(f"start span {name}", exc)
            yield _NoopSpan()
            return

        span = _LangfuseObservation(
            observation,
            self._root.redactor,
            metadata=child_metadata,
        )
        try:
            yield span
        except asyncio.CancelledError:
            span.update(level="WARNING", status_message="cancelled")
            raise
        except Exception as exc:
            span.update(level="ERROR", status_message=type(exc).__name__)
            raise
        finally:
            _safe_exit(manager)

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        _safe_exit(self._propagation_manager)
        _safe_exit(self._root_manager)


class _LangfuseObservation:
    def __init__(
        self,
        observation: Any,
        redactor: _TextRedactor,
        *,
        metadata: TelemetryMetadata | None = None,
    ) -> None:
        self.observation = observation
        self.redactor = redactor
        self._metadata = _metadata_dict(metadata)

    def update(
        self,
        *,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: TelemetryMetadata | None = None,
        level: TelemetryLevel | None = None,
        status_message: str | None = None,
    ) -> None:
        if metadata:
            self._metadata.update(_metadata_dict(metadata))
        arguments: dict[str, object] = {}
        if input_text is not None:
            content = self.redactor.content(input_text)
            if content is not None:
                arguments["input"] = content
        if output_text is not None:
            content = self.redactor.content(output_text)
            if content is not None:
                arguments["output"] = content
        if self._metadata:
            arguments["metadata"] = dict(self._metadata)
        if level is not None:
            arguments["level"] = level
        if status_message is not None:
            arguments["status_message"] = status_message
        if not arguments:
            return
        try:
            self.observation.update(**arguments)
        except Exception as exc:
            _log_sdk_failure("update observation", exc)

    def start_as_current_observation(self, **arguments: object) -> Any:
        return self.observation.start_as_current_observation(**arguments)


class _TextRedactor:
    def __init__(self, sensitive_values: Iterable[str]) -> None:
        self._sensitive_values = tuple(
            sorted(
                {value.strip() for value in sensitive_values if len(value.strip()) >= 4},
                key=len,
                reverse=True,
            )
        )

    def content(self, value: str | None) -> str | None:
        if value is None:
            return None
        return redact_text(value, self._sensitive_values)


_PEM_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]+-----.*?-----END [A-Z0-9 ]+-----", re.IGNORECASE | re.DOTALL
)
_BEARER_PATTERN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]+")
_URI_CREDENTIAL_PATTERN = re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^/\s:@]+:)[^@\s/]+(@)")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(?P<prefix>\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|"
    r"auth(?:entication)?[_ -]?token|token|password|passwd|secret|"
    r"webhook(?:[_ -]?url)?|private[_ -]?key|app[_ -]?secret)\b\s*[:=]\s*)"
    r"(?P<quote>[\"']?)(?P<value>[^\s,;&\"']+)(?P=quote)"
)
_ENV_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(?P<prefix>\b[A-Z][A-Z0-9_]*?"
    r"(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?|WEBHOOK)\b\s*[:=]\s*)"
    r"(?P<quote>[\"']?)(?P<value>[^\s,;&\"']+)(?P=quote)"
)
_GENERIC_SECRET_PATTERN = re.compile(r"(?i)\b(?:sk|pk)-[A-Za-z0-9_-]{8,}\b")


def redact_text(value: str, sensitive_values: Iterable[str] = ()) -> str:
    """Redact common credentials and configured secret values from text."""

    redacted = _PEM_PATTERN.sub("[REDACTED]", value)
    for secret in sorted(
        {item.strip() for item in sensitive_values if len(item.strip()) >= 4},
        key=len,
        reverse=True,
    ):
        redacted = redacted.replace(secret, "[REDACTED]")
    redacted = _BEARER_PATTERN.sub(r"\1[REDACTED]", redacted)
    redacted = _URI_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]\2", redacted)
    redacted = _SECRET_ASSIGNMENT_PATTERN.sub(_redact_assignment, redacted)
    redacted = _ENV_SECRET_ASSIGNMENT_PATTERN.sub(_redact_assignment, redacted)
    return _GENERIC_SECRET_PATTERN.sub("[REDACTED]", redacted)


def create_agent_telemetry(config: AgentConfig) -> AgentTelemetry:
    """Create Langfuse telemetry when it is configured and available."""

    settings = config.observability
    if not settings.enabled:
        return NoopAgentTelemetry()
    public_key = _credential_from_environment_or_config("LANGFUSE_PUBLIC_KEY", settings.public_key)
    secret_key = _credential_from_environment_or_config("LANGFUSE_SECRET_KEY", settings.secret_key)
    if not public_key or not secret_key:
        logger.warning("Langfuse telemetry is enabled but project credentials are unavailable.")
        return NoopAgentTelemetry()
    try:
        module = importlib.import_module("langfuse")
        client_type = module.Langfuse
        propagate_attributes = module.propagate_attributes
        client = client_type(
            public_key=public_key,
            secret_key=secret_key,
            base_url=settings.base_url,
            sample_rate=settings.sample_rate,
            release=__version__,
            environment="production",
        )
    except ImportError:
        logger.warning("Langfuse telemetry is enabled but the SDK is unavailable.")
        return NoopAgentTelemetry()
    except Exception as exc:
        _log_sdk_failure("initialize client", exc)
        return NoopAgentTelemetry()
    return LangfuseAgentTelemetry(
        client,
        propagate_attributes,
        capture_content=True,
        sensitive_values=_configured_sensitive_values(config, public_key, secret_key),
    )


def _credential_from_environment_or_config(environment_name: str, configured_value: str) -> str:
    """Prefer a process credential while supporting Dashboard-saved credentials."""

    return os.environ.get(environment_name, "").strip() or configured_value.strip()


def _configured_sensitive_values(
    config: AgentConfig,
    public_key: str,
    secret_key: str,
) -> tuple[str, ...]:
    values = [config.feishu_app_secret, public_key, secret_key]
    for name in (
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
        "FEISHU_APP_SECRET",
        "LARK_APP_SECRET",
    ):
        value = os.environ.get(name)
        if value:
            values.append(value)
    return tuple(values)


def _run_metadata(
    *,
    run_id: str,
    event_id: str,
    chat_type: str,
    workspace_id: UUID | None,
    provider: str,
    model: str,
    reasoning_effort: str,
) -> dict[str, MetadataValue]:
    metadata: dict[str, MetadataValue] = {
        "lumon_run_id": _bounded(run_id),
        "lumon_event_id": _bounded(event_id),
        "chat_type": _bounded(chat_type),
        "provider": _bounded(provider),
        "model": _bounded(model),
        "reasoning_effort": _bounded(reasoning_effort),
    }
    if workspace_id is not None:
        metadata["workspace_id"] = str(workspace_id)
    return metadata


def _metadata_dict(metadata: TelemetryMetadata | None) -> dict[str, MetadataValue]:
    if metadata is None:
        return {}
    return dict(metadata)


def _user_reference(sender_id: str) -> str | None:
    if not sender_id:
        return None
    digest = hashlib.sha256(sender_id.encode("utf-8")).hexdigest()[:16]
    return f"user_{digest}"


def _bounded(value: str, limit: int = 200) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _redact_assignment(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}{match.group('quote')}[REDACTED]{match.group('quote')}"


def _safe_exit(manager: Any | None) -> None:
    if manager is None:
        return
    try:
        manager.__exit__(None, None, None)
    except Exception as exc:
        _log_sdk_failure("close observation", exc)


def _log_sdk_failure(action: str, error: Exception) -> None:
    logger.warning("Langfuse telemetry %s failed (%s).", action, type(error).__name__)
