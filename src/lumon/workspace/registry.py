"""Persist the user's known Lumon Workspaces outside the Workspace itself."""

from __future__ import annotations

import os
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from lumon.errors import PreflightError
from lumon.workspace.config import load_workspace_config
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest

REGISTRY_SCHEMA_VERSION = 1
LUMON_HOME_ENV = "LUMON_HOME"


@dataclass(frozen=True, slots=True)
class UserStateLayout:
    """Resolve user-level Lumon state without creating any directories."""

    root: Path

    @classmethod
    def from_root(cls, root: Path | None = None) -> UserStateLayout:
        """Resolve an explicit root, ``LUMON_HOME``, or the default home path."""

        configured = root or (
            Path(os.environ[LUMON_HOME_ENV]) if os.environ.get(LUMON_HOME_ENV) else None
        )
        state_root = configured or (Path.home() / ".lumon")
        return cls(state_root.expanduser().resolve())

    @property
    def registry(self) -> Path:
        """Return the machine-local Workspace registry path."""

        return self.root / "registry.toml"

    @property
    def profiles(self) -> Path:
        """Return the parent directory for per-Workspace profiles."""

        return self.root / "workspaces"

    def profile(self, workspace_id: UUID) -> Path:
        """Return one Workspace's user-level configuration file."""

        return self.profiles / str(workspace_id) / "config.toml"


@dataclass(frozen=True, slots=True)
class WorkspaceRegistration:
    """One validated Workspace known to the current user."""

    workspace_id: UUID
    name: str
    path: Path
    registered_at: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation for the Dashboard seam."""

        return {
            "workspace_id": str(self.workspace_id),
            "name": self.name,
            "path": str(self.path),
            "registered_at": self.registered_at,
        }


class WorkspaceRegistry:
    """Read and atomically update the user's typed Workspace registry."""

    def __init__(
        self,
        state_root: Path | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.layout = UserStateLayout.from_root(state_root)
        self._now = now or (lambda: datetime.now(UTC))

    def list(self) -> tuple[WorkspaceRegistration, ...]:
        """Load all registered Workspaces, or an empty tuple when unconfigured."""

        if not self.layout.registry.exists():
            return ()
        try:
            payload = tomllib.loads(self.layout.registry.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PreflightError(
                f"Unable to read Lumon Workspace registry: {self.layout.registry}"
            ) from exc

        schema_version = payload.get("schema_version")
        if (
            not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version != REGISTRY_SCHEMA_VERSION
        ):
            raise PreflightError(f"Unsupported Lumon Workspace registry: {self.layout.registry}")

        raw_workspaces = payload.get("workspaces", [])
        if not isinstance(raw_workspaces, list):
            raise PreflightError(
                f"Workspace registry entries must be an array: {self.layout.registry}"
            )

        registrations: list[WorkspaceRegistration] = []
        ids: set[UUID] = set()
        paths: set[Path] = set()
        for index, raw_workspace in enumerate(cast(list[object], raw_workspaces)):
            registration = _parse_registration(raw_workspace, self.layout.registry, index)
            if registration.workspace_id in ids:
                raise PreflightError(
                    f"Duplicate Workspace ID at index {index}: {self.layout.registry}"
                )
            if registration.path in paths:
                raise PreflightError(
                    f"Duplicate Workspace path at index {index}: {self.layout.registry}"
                )
            ids.add(registration.workspace_id)
            paths.add(registration.path)
            registrations.append(registration)
        return tuple(registrations)

    def find(self, workspace_id: UUID) -> WorkspaceRegistration | None:
        """Find one Workspace by its stable manifest ID."""

        return next((item for item in self.list() if item.workspace_id == workspace_id), None)

    def find_by_path(self, path: Path) -> WorkspaceRegistration | None:
        """Find one Workspace by its canonical filesystem path."""

        canonical = path.expanduser().resolve()
        return next((item for item in self.list() if item.path == canonical), None)

    def register(self, path: Path) -> WorkspaceRegistration:
        """Validate and add or refresh one Workspace without touching its files."""

        layout = WorkspaceLayout.from_root(path)
        if not layout.root.is_dir():
            raise PreflightError(f"Workspace is not a directory: {layout.root}")
        manifest = load_manifest(layout.manifest)
        config = load_workspace_config(layout.workspace_config)
        if config.name != manifest.name:
            raise PreflightError(
                f"Workspace name differs between manifest and configuration: {layout.root}"
            )

        existing = self.list()
        for registration in existing:
            if (
                registration.path == layout.root
                and registration.workspace_id != manifest.workspace_id
            ):
                raise PreflightError(
                    f"Workspace path is already registered with another ID: {layout.root}"
                )

        previous = next(
            (item for item in existing if item.workspace_id == manifest.workspace_id),
            None,
        )
        registration = WorkspaceRegistration(
            workspace_id=manifest.workspace_id,
            name=manifest.name,
            path=layout.root,
            registered_at=previous.registered_at if previous else _timestamp(self._now()),
        )
        replacements = [
            registration if item.workspace_id == registration.workspace_id else item
            for item in existing
        ]
        if previous is None:
            replacements.append(registration)
        self._write(replacements)
        return registration

    def raw_snapshot(self) -> bytes | None:
        """Capture the exact registry bytes for a surrounding transaction."""

        if not self.layout.registry.exists():
            return None
        try:
            return self.layout.registry.read_bytes()
        except OSError as exc:
            raise PreflightError(
                f"Unable to snapshot Lumon Workspace registry: {self.layout.registry}"
            ) from exc

    def restore_raw(self, snapshot: bytes | None) -> None:
        """Restore a previous registry snapshot after a failed transaction."""

        if snapshot is None:
            try:
                self.layout.registry.unlink(missing_ok=True)
            except OSError as exc:
                raise PreflightError(
                    f"Unable to roll back Lumon Workspace registry: {self.layout.registry}"
                ) from exc
            return
        _atomic_write(self.layout.registry, snapshot, mode=0o600)

    def _write(self, registrations: list[WorkspaceRegistration]) -> None:
        try:
            self.layout.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PreflightError(
                f"Unable to create Lumon user state directory: {self.layout.root}"
            ) from exc
        _secure_directory(self.layout.root)
        _atomic_write(self.layout.registry, _render(registrations).encode("utf-8"), mode=0o600)


def _parse_registration(value: object, source: Path, index: int) -> WorkspaceRegistration:
    if not isinstance(value, dict):
        raise PreflightError(f"Invalid Workspace registry entry at index {index}: {source}")
    fields = cast(dict[str, object], value)
    raw_id = fields.get("workspace_id")
    name = fields.get("name")
    raw_path = fields.get("path")
    registered_at = fields.get("registered_at")
    if not isinstance(raw_id, str) or not _is_uuid(raw_id):
        raise PreflightError(f"Invalid Workspace ID at index {index}: {source}")
    if not isinstance(name, str) or not name.strip():
        raise PreflightError(f"Invalid Workspace name at index {index}: {source}")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise PreflightError(f"Invalid Workspace path at index {index}: {source}")
    if not isinstance(registered_at, str) or not registered_at.strip():
        raise PreflightError(f"Invalid Workspace registration time at index {index}: {source}")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise PreflightError(
            f"Workspace registry paths must be absolute at index {index}: {source}"
        )
    path = path.resolve()
    return WorkspaceRegistration(UUID(raw_id), name, path, registered_at)


def _render(registrations: list[WorkspaceRegistration]) -> str:
    lines = [f"schema_version = {REGISTRY_SCHEMA_VERSION}"]
    for registration in registrations:
        lines.extend(
            [
                "",
                "[[workspaces]]",
                f"workspace_id = {_toml_string(str(registration.workspace_id))}",
                f"name = {_toml_string(registration.name)}",
                f"path = {_toml_string(str(registration.path))}",
                f"registered_at = {_toml_string(registration.registered_at)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _timestamp(now: datetime) -> str:
    return now.astimezone(UTC).isoformat()


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _secure_directory(path: Path) -> None:
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Lumon user directory: {path}") from exc


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        raise PreflightError(f"Unable to write Lumon user state: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
