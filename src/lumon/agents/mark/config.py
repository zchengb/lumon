"""Typed, user-level configuration for the Mark Agent."""

from __future__ import annotations

import os
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from lumon.errors import AgentConfigError
from lumon.workspace.registry import UserStateLayout

MARK_CONFIG_SCHEMA_VERSION = 1
ExecutionMode = Literal["full_access"]
ResponseMode = Literal["progress_and_final"]


@dataclass(frozen=True, slots=True)
class MarkAgentConfig:
    """The complete configuration required to run Mark."""

    schema_version: int = MARK_CONFIG_SCHEMA_VERSION
    enabled: bool = False
    default_workspace_id: UUID | None = None
    execution_mode: ExecutionMode = "full_access"
    response_mode: ResponseMode = "progress_and_final"
    codex_model: str | None = None
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

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
        if self.codex_model is not None and not self.codex_model.strip():
            raise AgentConfigError("Codex model must be empty or a non-empty name.")

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
            "codex_model": self.codex_model,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_configured": bool(self.feishu_app_secret),
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
    raw_model = payload.get("codex_model", "")
    raw_feishu = payload.get("feishu")

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
    if execution_mode != "full_access":
        raise AgentConfigError(f"Mark configuration must use full_access mode: {source}")
    if response_mode != "progress_and_final":
        raise AgentConfigError(f"Mark configuration must use progress_and_final: {source}")
    if raw_model is not None and not isinstance(raw_model, str):
        raise AgentConfigError(f"Invalid Codex model value: {source}")
    if not isinstance(raw_feishu, dict):
        raise AgentConfigError(f"Missing Feishu configuration: {source}")
    feishu = cast(dict[str, object], raw_feishu)
    app_id = feishu.get("app_id")
    app_secret = feishu.get("app_secret")
    if not isinstance(app_id, str) or not app_id.strip():
        raise AgentConfigError(f"Missing Feishu App ID: {source}")
    if not isinstance(app_secret, str) or not app_secret.strip():
        raise AgentConfigError(f"Missing Feishu App Secret: {source}")

    return MarkAgentConfig(
        schema_version=schema_version,
        enabled=enabled,
        default_workspace_id=workspace_id,
        execution_mode="full_access",
        response_mode="progress_and_final",
        codex_model=raw_model or None,
        feishu_app_id=app_id,
        feishu_app_secret=app_secret,
    )


def _parse_optional_uuid(value: str, source: Path) -> UUID | None:
    if not value.strip():
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise AgentConfigError(f"Invalid default Workspace ID: {source}") from exc


def _render(config: MarkAgentConfig) -> str:
    workspace_id = str(config.default_workspace_id) if config.default_workspace_id else ""
    model = config.codex_model or ""
    lines = [
        f"schema_version = {config.schema_version}",
        f"enabled = {'true' if config.enabled else 'false'}",
        f"default_workspace_id = {_toml_string(workspace_id)}",
        'execution_mode = "full_access"',
        'response_mode = "progress_and_final"',
        f"codex_model = {_toml_string(model)}",
        "",
        "[feishu]",
        f"app_id = {_toml_string(config.feishu_app_id)}",
        f"app_secret = {_toml_string(config.feishu_app_secret)}",
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
