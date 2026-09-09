"""Typed, user-level configuration for one Lumon Workspace."""

from __future__ import annotations

import os
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

from lumon.errors import InvalidInputError, PreflightError
from lumon.tools.feishu_webhook import validate_webhook_url
from lumon.workspace.registry import UserStateLayout

SETTINGS_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class FeishuWebhookSettings:
    """The v1 Feishu Webhook settings for one Workspace."""

    enabled: bool = False
    url: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceSettings:
    """All typed, mutable settings owned by one Workspace profile."""

    workspace_id: UUID
    feishu_webhook: FeishuWebhookSettings = FeishuWebhookSettings()


class WorkspaceSettingsStore:
    """Read and atomically update per-Workspace TOML profiles."""

    def __init__(self, state_root: Path | None = None) -> None:
        self.layout = UserStateLayout.from_root(state_root)

    def path_for(self, workspace_id: UUID) -> Path:
        """Return the user-level configuration path for one Workspace."""

        return self.layout.profile(workspace_id)

    def load(self, workspace_id: UUID) -> WorkspaceSettings:
        """Load a profile, returning safe defaults when it has not been created."""

        path = self.path_for(workspace_id)
        if not path.exists():
            return WorkspaceSettings(workspace_id)
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PreflightError(f"Unable to read Workspace settings: {path}") from exc
        return _parse_settings(payload, path, workspace_id)

    def ensure(self, workspace_id: UUID) -> WorkspaceSettings:
        """Create a default profile only when the Workspace has no profile yet."""

        path = self.path_for(workspace_id)
        if path.exists():
            _secure_file(path)
            return self.load(workspace_id)
        settings = WorkspaceSettings(workspace_id)
        self.save(settings)
        return settings

    def save(self, settings: WorkspaceSettings) -> None:
        """Validate and atomically write one profile with owner-only permissions."""

        if settings.feishu_webhook.url is not None:
            validate_webhook_url(settings.feishu_webhook.url)
        path = self.path_for(settings.workspace_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PreflightError(
                f"Unable to create Lumon Workspace profile directory: {path.parent}"
            ) from exc
        _secure_directory(self.layout.root)
        _secure_directory(self.layout.profiles)
        _secure_directory(path.parent)
        _atomic_write(path, _render(settings).encode("utf-8"), mode=0o600)

    def raw_snapshot(self, workspace_id: UUID) -> bytes | None:
        """Capture one profile's exact bytes for a surrounding transaction."""

        path = self.path_for(workspace_id)
        if not path.exists():
            return None
        try:
            return path.read_bytes()
        except OSError as exc:
            raise PreflightError(f"Unable to snapshot Workspace settings: {path}") from exc

    def restore_raw(self, workspace_id: UUID, snapshot: bytes | None) -> None:
        """Restore or remove one profile after a failed transaction."""

        path = self.path_for(workspace_id)
        if snapshot is None:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise PreflightError(f"Unable to roll back Workspace settings: {path}") from exc
            return
        _atomic_write(path, snapshot, mode=0o600)


def masked_webhook_url(url: str | None) -> str | None:
    """Return a display-safe URL that never exposes the Webhook token."""

    if not url:
        return None
    parsed = urlsplit(url)
    host = parsed.hostname or "configured"
    return f"{parsed.scheme}://{host}/••••"


def _parse_settings(
    payload: dict[str, object], source: Path, workspace_id: UUID
) -> WorkspaceSettings:
    schema_version = payload.get("schema_version")
    raw_id = payload.get("workspace_id")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != SETTINGS_SCHEMA_VERSION
    ):
        raise PreflightError(f"Unsupported Workspace settings schema: {source}")
    if not isinstance(raw_id, str) or raw_id != str(workspace_id):
        raise PreflightError(f"Workspace settings ID does not match its profile: {source}")

    raw_feishu = payload.get("feishu", {})
    if not isinstance(raw_feishu, dict):
        raise PreflightError(f"Invalid Feishu settings: {source}")
    raw_webhook = cast(dict[str, object], raw_feishu).get("webhook", {})
    if not isinstance(raw_webhook, dict):
        raise PreflightError(f"Invalid Feishu Webhook settings: {source}")
    webhook = cast(dict[str, object], raw_webhook)
    enabled = webhook.get("enabled", False)
    url = webhook.get("url")
    if not isinstance(enabled, bool):
        raise PreflightError(f"Invalid Feishu Webhook enabled value: {source}")
    if url is not None and (not isinstance(url, str) or not url.strip()):
        raise PreflightError(f"Invalid Feishu Webhook URL value: {source}")
    if isinstance(url, str):
        try:
            validate_webhook_url(url)
        except InvalidInputError as exc:
            raise PreflightError(f"Invalid Feishu Webhook URL value: {source}") from exc
    return WorkspaceSettings(
        workspace_id=workspace_id,
        feishu_webhook=FeishuWebhookSettings(enabled=enabled, url=url),
    )


def _render(settings: WorkspaceSettings) -> str:
    lines = [
        f"schema_version = {SETTINGS_SCHEMA_VERSION}",
        f"workspace_id = {_toml_string(str(settings.workspace_id))}",
        "",
        "[feishu.webhook]",
        f"enabled = {'true' if settings.feishu_webhook.enabled else 'false'}",
    ]
    if settings.feishu_webhook.url:
        lines.append(f"url = {_toml_string(settings.feishu_webhook.url)}")
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _secure_directory(path: Path) -> None:
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Lumon user directory: {path}") from exc


def _secure_file(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Workspace settings: {path}") from exc


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
        raise PreflightError(f"Unable to write Workspace settings: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
