"""Read and write the small, inspectable Workspace manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from lumon.errors import PreflightError

MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class WorkspaceManifest:
    """Metadata proving that a directory is a v1 Lumon Workspace."""

    schema_version: int
    workspace_id: UUID
    name: str
    created_at: str
    lumon_version: str
    status: str

    @classmethod
    def create(
        cls, name: str, lumon_version: str, now: datetime | None = None
    ) -> WorkspaceManifest:
        """Create a new manifest with a UTC timestamp and unique ID."""

        timestamp = now or datetime.now(UTC)
        return cls(
            schema_version=MANIFEST_SCHEMA_VERSION,
            workspace_id=uuid4(),
            name=name,
            created_at=timestamp.astimezone(UTC).isoformat(),
            lumon_version=lumon_version,
            status="initialized",
        )

    @classmethod
    def from_dict(cls, value: object, source: Path) -> WorkspaceManifest:
        """Validate untrusted JSON before exposing a typed manifest."""

        if not isinstance(value, dict):
            raise PreflightError(f"Workspace manifest is not an object: {source}")

        fields = cast(dict[str, object], value)
        schema_version = fields.get("schema_version")
        workspace_id = fields.get("workspace_id")
        name = fields.get("name")
        created_at = fields.get("created_at")
        lumon_version = fields.get("lumon_version")
        status = fields.get("status")

        if (
            not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version != MANIFEST_SCHEMA_VERSION
        ):
            raise PreflightError(f"Unsupported Workspace manifest schema at {source}")
        if not isinstance(workspace_id, str) or not _is_uuid(workspace_id):
            raise PreflightError(f"Workspace manifest has an invalid workspace_id: {source}")
        if not isinstance(name, str) or not name.strip():
            raise PreflightError(f"Workspace manifest has an invalid name: {source}")
        if not isinstance(created_at, str) or not created_at.strip():
            raise PreflightError(f"Workspace manifest has an invalid created_at: {source}")
        if not isinstance(lumon_version, str) or not lumon_version.strip():
            raise PreflightError(f"Workspace manifest has an invalid lumon_version: {source}")
        if status != "initialized":
            raise PreflightError(f"Workspace manifest has an invalid status: {source}")

        return cls(
            schema_version=schema_version,
            workspace_id=UUID(workspace_id),
            name=name,
            created_at=created_at,
            lumon_version=lumon_version,
            status="initialized",
        )

    def to_dict(self) -> dict[str, object]:
        """Return the stable on-disk representation."""

        return {
            "schema_version": self.schema_version,
            "workspace_id": str(self.workspace_id),
            "name": self.name,
            "created_at": self.created_at,
            "lumon_version": self.lumon_version,
            "status": self.status,
        }

    def write(self, path: Path) -> None:
        """Write formatted JSON to a path inside a staged Workspace."""

        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def load_manifest(path: Path) -> WorkspaceManifest:
    """Load and validate a manifest without accepting arbitrary dicts."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"Unable to read Workspace manifest: {path}") from exc
    return WorkspaceManifest.from_dict(value, path)


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True
