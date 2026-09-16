"""Typed, user-level configuration for the Mark Agent."""

from __future__ import annotations

import os
import tempfile
import tomllib
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse
from uuid import UUID

from lumon.agents.mark.model import AgentProvider
from lumon.errors import AgentConfigError
from lumon.workspace.registry import UserStateLayout

MARK_CONFIG_SCHEMA_VERSION = 1
DEFAULT_AGENT_MODEL = "gpt-5.6-luna"
DEFAULT_AGENT_REASONING_EFFORT = "max"
DEFAULT_LANGFUSE_BASE_URL = "https://cloud.langfuse.com"
ExecutionMode = Literal["full_access"]
ResponseMode = Literal["progress_and_final"]
AgentReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh", "max", "ultra"]
ObservabilityProvider = Literal["langfuse"]
_AGENT_REASONING_EFFORTS = frozenset({"minimal", "low", "medium", "high", "xhigh", "max", "ultra"})


@dataclass(frozen=True, slots=True)
class ObservabilityConfig:
    """Optional Langfuse Cloud settings for Mark telemetry."""

    enabled: bool = False
    provider: ObservabilityProvider = "langfuse"
    base_url: str = DEFAULT_LANGFUSE_BASE_URL
    # Retained for compatibility with existing agent.toml files. Content
    # capture is now always enabled and redacted before it reaches Langfuse.
    capture_content: bool = True
    sample_rate: float = 1.0
    public_key: str = ""
    secret_key: str = ""

    def __post_init__(self) -> None:
        """Keep the formerly optional capture setting enabled everywhere."""

        object.__setattr__(self, "capture_content", True)

    def validate(self) -> None:
        """Validate the provider settings before they cross the config seam."""

        if self.provider != "langfuse":
            raise AgentConfigError(f"Unsupported observability provider: {self.provider}")
        if not self.base_url.strip():
            raise AgentConfigError("Observability base URL must be a non-empty URL.")
        try:
            parsed_url = urlparse(self.base_url)
        except ValueError as exc:
            raise AgentConfigError("Observability base URL must be a valid URL.") from exc
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise AgentConfigError(
                "Observability base URL must include an HTTP(S) scheme and host."
            )
        if parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
            raise AgentConfigError(
                "Observability base URL must not include credentials or query data."
            )
        if not isfinite(self.sample_rate) or not 0.0 <= self.sample_rate <= 1.0:
            raise AgentConfigError("Observability sample rate must be between 0 and 1.")

    def to_safe_dict(self) -> dict[str, object]:
        """Return settings that contain no observability credentials."""

        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "base_url": self.base_url,
            "capture_content": self.capture_content,
            "sample_rate": self.sample_rate,
        }


@dataclass(frozen=True, slots=True)
class MarkAgentConfig:
    """The complete configuration required to run Mark."""

    schema_version: int = MARK_CONFIG_SCHEMA_VERSION
    enabled: bool = False
    default_workspace_id: UUID | None = None
    execution_mode: ExecutionMode = "full_access"
    response_mode: ResponseMode = "progress_and_final"
    agent_provider: AgentProvider = "codex"
    agent_model: str = DEFAULT_AGENT_MODEL
    agent_reasoning_effort: AgentReasoningEffort = DEFAULT_AGENT_REASONING_EFFORT
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)

    def validate(self) -> None:
        """Validate values before they cross the on-disk configuration seam."""

        if self.schema_version != MARK_CONFIG_SCHEMA_VERSION:
            raise AgentConfigError("Unsupported Mark Agent configuration schema.")
        if self.execution_mode != "full_access":
            raise AgentConfigError("Mark requires execution_mode = full_access.")
        if self.response_mode != "progress_and_final":
            raise AgentConfigError("Mark requires response_mode = progress_and_final.")
        if not self.feishu_app_id.strip():
            raise AgentConfigError("Feishu App ID is missing from Mark configuration.")
        if not self.feishu_app_secret.strip():
            raise AgentConfigError("Feishu App Secret is missing from Mark configuration.")
        if self.agent_provider != "codex":
            raise AgentConfigError(f"Unsupported Mark Agent provider: {self.agent_provider}")
        if not self.agent_model.strip():
            raise AgentConfigError("Agent model must be a non-empty name.")
        if self.agent_reasoning_effort not in _AGENT_REASONING_EFFORTS:
            raise AgentConfigError("Unsupported Agent reasoning effort.")
        self.observability.validate()

    def to_safe_dict(self) -> dict[str, object]:
        """Return a diagnostic representation that excludes the App Secret."""

        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "default_workspace_id": (
                str(self.default_workspace_id) if self.default_workspace_id else None
            ),
            "execution_mode": self.execution_mode,
            "response_mode": self.response_mode,
            "agent_provider": self.agent_provider,
            "agent_model": self.agent_model,
            "agent_reasoning_effort": self.agent_reasoning_effort,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_configured": bool(self.feishu_app_secret),
            "observability": self.observability.to_safe_dict(),
        }


class MarkConfigStore:
    """Read and atomically write the user's Mark configuration."""

    def __init__(self, state_root: Path | None = None) -> None:
        self.layout = UserStateLayout.from_root(state_root)

    @property
    def path(self) -> Path:
        """Return the configuration path without creating it."""

        return self.layout.root / "agent.toml"

    def load(self) -> MarkAgentConfig:
        """Load and validate Mark configuration without exposing secret values."""

        if not self.path.is_file():
            raise AgentConfigError(
                f"Mark is not configured yet: {self.path}. Run `lumon agent configure`."
            )
        if not self.is_owner_only():
            raise AgentConfigError(f"Mark configuration must have file mode 600: {self.path}")
        try:
            payload = tomllib.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise AgentConfigError(f"Unable to read Mark configuration: {self.path}") from exc

        config = _parse_config(payload, self.path)
        config.validate()
        return config

    def save(self, config: MarkAgentConfig) -> None:
        """Validate and atomically write Mark configuration with mode ``600``."""

        config.validate()
        try:
            self.layout.root.mkdir(parents=True, exist_ok=True)
            self.layout.root.chmod(0o700)
        except OSError as exc:
            raise AgentConfigError(
                f"Unable to create secure Lumon user state directory: {self.layout.root}"
            ) from exc
        _atomic_write(self.path, _render(config).encode("utf-8"), mode=0o600)

    def is_owner_only(self) -> bool:
        """Return whether an existing configuration is readable only by its owner."""

        if not self.path.exists():
            return False
        try:
            return self.path.stat().st_mode & 0o777 == 0o600
        except OSError:
            return False


def _parse_config(payload: dict[str, object], source: Path) -> MarkAgentConfig:
    schema_version = payload.get("schema_version")
    enabled = payload.get("enabled")
    raw_workspace_id = payload.get("default_workspace_id", "")
    execution_mode = payload.get("execution_mode")
    response_mode = payload.get("response_mode")
    raw_provider = payload.get("agent_provider", "codex")
    # ``codex_model`` is read only for existing v1 files; new files never write it.
    raw_model = payload.get("agent_model", payload.get("codex_model", DEFAULT_AGENT_MODEL))
    raw_reasoning_effort = payload.get("agent_reasoning_effort", DEFAULT_AGENT_REASONING_EFFORT)
    raw_feishu = payload.get("feishu")
    raw_observability = payload.get("observability", {})

    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != MARK_CONFIG_SCHEMA_VERSION
    ):
        raise AgentConfigError(f"Unsupported Mark Agent configuration schema: {source}")
    if not isinstance(enabled, bool):
        raise AgentConfigError(f"Invalid Mark enabled value: {source}")
    if not isinstance(raw_workspace_id, str):
        raise AgentConfigError(f"Invalid default Workspace ID: {source}")
    workspace_id = _parse_optional_uuid(raw_workspace_id, source)
    if not isinstance(raw_provider, str) or raw_provider != "codex":
        raise AgentConfigError(f"Unsupported Mark Agent provider: {source}")
    if execution_mode != "full_access":
        raise AgentConfigError(f"Mark configuration must use full_access mode: {source}")
    if response_mode != "progress_and_final":
        raise AgentConfigError(f"Mark configuration must use progress_and_final: {source}")
    if raw_model is not None and not isinstance(raw_model, str):
        raise AgentConfigError(f"Invalid Agent model value: {source}")
    if (
        not isinstance(raw_reasoning_effort, str)
        or raw_reasoning_effort not in _AGENT_REASONING_EFFORTS
    ):
        raise AgentConfigError(f"Invalid Agent reasoning effort: {source}")
    if not isinstance(raw_feishu, dict):
        raise AgentConfigError(f"Missing Feishu configuration: {source}")
    feishu = cast(dict[str, object], raw_feishu)
    app_id = feishu.get("app_id")
    app_secret = feishu.get("app_secret")
    if not isinstance(app_id, str) or not app_id.strip():
        raise AgentConfigError(f"Missing Feishu App ID: {source}")
    if not isinstance(app_secret, str) or not app_secret.strip():
        raise AgentConfigError(f"Missing Feishu App Secret: {source}")
    if not isinstance(raw_observability, dict):
        raise AgentConfigError(f"Invalid observability configuration: {source}")
    observability = _parse_observability(cast(dict[str, object], raw_observability), source)

    return MarkAgentConfig(
        schema_version=schema_version,
        enabled=enabled,
        default_workspace_id=workspace_id,
        execution_mode="full_access",
        response_mode="progress_and_final",
        agent_provider="codex",
        agent_model=raw_model or DEFAULT_AGENT_MODEL,
        agent_reasoning_effort=cast(AgentReasoningEffort, raw_reasoning_effort),
        feishu_app_id=app_id,
        feishu_app_secret=app_secret,
        observability=observability,
    )


def _parse_observability(payload: dict[str, object], source: Path) -> ObservabilityConfig:
    enabled = payload.get("enabled", False)
    provider = payload.get("provider", "langfuse")
    base_url = payload.get("base_url", DEFAULT_LANGFUSE_BASE_URL)
    capture_content = payload.get("capture_content", True)
    sample_rate = payload.get("sample_rate", 1.0)
    public_key = payload.get("public_key", "")
    secret_key = payload.get("secret_key", "")
    if not isinstance(enabled, bool):
        raise AgentConfigError(f"Invalid observability enabled value: {source}")
    if not isinstance(provider, str) or provider != "langfuse":
        raise AgentConfigError(f"Unsupported observability provider: {source}")
    if not isinstance(base_url, str):
        raise AgentConfigError(f"Invalid observability base URL: {source}")
    if not isinstance(capture_content, bool):
        raise AgentConfigError(f"Invalid observability content capture value: {source}")
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, (int, float)):
        raise AgentConfigError(f"Invalid observability sample rate: {source}")
    if not isinstance(public_key, str):
        raise AgentConfigError(f"Invalid Langfuse public key: {source}")
    if not isinstance(secret_key, str):
        raise AgentConfigError(f"Invalid Langfuse secret key: {source}")
    config = ObservabilityConfig(
        enabled=enabled,
        provider="langfuse",
        base_url=base_url,
        capture_content=capture_content,
        sample_rate=float(sample_rate),
        public_key=public_key,
        secret_key=secret_key,
    )
    try:
        config.validate()
    except AgentConfigError as exc:
        raise AgentConfigError(f"Invalid observability configuration: {source}") from exc
    return config


def _parse_optional_uuid(value: str, source: Path) -> UUID | None:
    if not value.strip():
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise AgentConfigError(f"Invalid default Workspace ID: {source}") from exc


def _render(config: MarkAgentConfig) -> str:
    workspace_id = str(config.default_workspace_id) if config.default_workspace_id else ""
    lines = [
        f"schema_version = {config.schema_version}",
        f"enabled = {'true' if config.enabled else 'false'}",
        f"default_workspace_id = {_toml_string(workspace_id)}",
        'execution_mode = "full_access"',
        'response_mode = "progress_and_final"',
        f"agent_provider = {_toml_string(config.agent_provider)}",
        f"agent_model = {_toml_string(config.agent_model)}",
        f"agent_reasoning_effort = {_toml_string(config.agent_reasoning_effort)}",
        "",
        "[feishu]",
        f"app_id = {_toml_string(config.feishu_app_id)}",
        f"app_secret = {_toml_string(config.feishu_app_secret)}",
        "",
        "[observability]",
        f"enabled = {'true' if config.observability.enabled else 'false'}",
        f"provider = {_toml_string(config.observability.provider)}",
        f"base_url = {_toml_string(config.observability.base_url)}",
        f"capture_content = {'true' if config.observability.capture_content else 'false'}",
        f"sample_rate = {config.observability.sample_rate}",
        f"public_key = {_toml_string(config.observability.public_key)}",
        f"secret_key = {_toml_string(config.observability.secret_key)}",
    ]
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(mode)
    except OSError as exc:
        raise AgentConfigError(f"Unable to write Mark configuration: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
