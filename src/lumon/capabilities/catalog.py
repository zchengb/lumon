"""Discover and safely manage Workspace capability Markdown files."""

from __future__ import annotations

import os
import re
import tempfile
import tomllib
from pathlib import Path

from lumon.capabilities.model import (
    CapabilityCatalogSnapshot,
    CapabilityDefinition,
    CapabilityDiagnostic,
)
from lumon.errors import PreflightError

_CAPABILITY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_CAPABILITY_SUFFIX = ".md"
_CAPABILITY_DELIMITER = "---"


class CapabilityValidationError(PreflightError):
    """Raised when a capability file or capability mutation is invalid."""


class CapabilityCatalog:
    """Read and atomically update capabilities below one Workspace root."""

    def __init__(self, workspace: Path) -> None:
        from lumon.workspace.layout import WorkspaceLayout

        self.layout = WorkspaceLayout.from_root(workspace)

    def discover(self) -> CapabilityCatalogSnapshot:
        """Load every Markdown capability, retaining safe diagnostics."""

        directory = self.layout.capabilities_dir
        if not directory.exists():
            return CapabilityCatalogSnapshot()
        if not directory.is_dir() or directory.is_symlink():
            return CapabilityCatalogSnapshot(
                diagnostics=(
                    CapabilityDiagnostic(
                        directory,
                        "capability directory is not a regular directory",
                    ),
                )
            )

        definitions: list[CapabilityDefinition] = []
        diagnostics: list[CapabilityDiagnostic] = []
        for path in sorted(directory.glob(f"*{_CAPABILITY_SUFFIX}"), key=lambda item: item.name):
            if path.name.startswith("."):
                continue
            if path.is_symlink():
                diagnostics.append(
                    CapabilityDiagnostic(path, "capability path must not be a symbolic link")
                )
                continue
            if not path.is_file():
                diagnostics.append(
                    CapabilityDiagnostic(path, "capability path must be a regular file")
                )
                continue
            try:
                definitions.append(self._read(path))
            except CapabilityValidationError as exc:
                diagnostics.append(CapabilityDiagnostic(path, str(exc)))

        duplicate_ids = _duplicate_ids(definitions)
        if duplicate_ids:
            kept: list[CapabilityDefinition] = []
            for definition in definitions:
                if definition.capability_id in duplicate_ids:
                    diagnostics.append(
                        CapabilityDiagnostic(
                            self.layout.root / definition.path,
                            f"duplicate capability id: {definition.capability_id}",
                        )
                    )
                else:
                    kept.append(definition)
            definitions = kept
        return CapabilityCatalogSnapshot(tuple(definitions), tuple(diagnostics))

    def read(self, capability_id: str) -> CapabilityDefinition:
        """Read one capability by its validated ID."""

        self._path_for_id(capability_id)
        matches = tuple(
            item for item in self.discover().definitions if item.capability_id == capability_id
        )
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise CapabilityValidationError(f"duplicate capability id: {capability_id}")

        path = self._path_for_id(capability_id)
        if path.is_file() and not path.is_symlink():
            definition = self._read(path)
            raise CapabilityValidationError(
                f"Capability id is not present in its requested file: {definition.capability_id}"
            )
        raise CapabilityValidationError(f"Capability does not exist: {capability_id}")

    def read_raw(self, capability_name: str) -> tuple[Path, str]:
        """Read safe Markdown so the Dashboard can repair invalid content."""

        path = self._path_for_name(capability_name)
        if not path.is_file() or path.is_symlink():
            raise CapabilityValidationError(f"Capability does not exist: {capability_name}")
        try:
            return self._display_path(path), path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CapabilityValidationError(f"Unable to read capability: {path.name}") from exc

    def create(self, content: str) -> CapabilityDefinition:
        """Validate and create a new capability without replacing a file."""

        definition = _parse_capability(content, None)
        self._ensure_directory()
        path = self._path_for_id(definition.capability_id)
        if path.exists() or path.is_symlink():
            raise CapabilityValidationError(
                f"Capability already exists: {definition.capability_id}"
            )
        _atomic_write(path, definition.content.encode("utf-8"))
        return self._read(path)

    def save(
        self,
        content: str,
        *,
        expected_id: str | None = None,
    ) -> CapabilityDefinition:
        """Validate, save, and optionally rename one capability file."""

        definition = _parse_capability(content, None)
        self._ensure_directory()
        path = self._path_for_id(definition.capability_id)
        source = self._path_for_id(expected_id) if expected_id is not None else path
        current = self._find_definition(expected_id) if expected_id is not None else None
        if current is not None:
            source = self._absolute_path(current.path)
        if expected_id is not None and definition.capability_id == expected_id:
            path = source
        if source.is_symlink():
            raise CapabilityValidationError(f"Capability path is a symbolic link: {source.name}")
        if path != source:
            if path.exists() or path.is_symlink():
                raise CapabilityValidationError(
                    f"Capability already exists: {definition.capability_id}"
                )
            _atomic_write(path, definition.content.encode("utf-8"))
            try:
                source.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                try:
                    path.unlink()
                except OSError:
                    pass
                raise CapabilityValidationError(
                    f"Unable to rename capability: {source.name}"
                ) from exc
            return self._read(path)
        if path.is_symlink():
            raise CapabilityValidationError(f"Capability path is a symbolic link: {path.name}")
        _atomic_write(path, definition.content.encode("utf-8"))
        return self._read(path)

    def delete(self, capability_id: str) -> None:
        """Delete one capability file without touching other Workspace paths."""

        current = (
            self._find_definition(capability_id)
            if _CAPABILITY_ID_RE.fullmatch(capability_id.strip())
            else None
        )
        path = (
            self._absolute_path(current.path)
            if current is not None
            else self._path_for_name(capability_id)
        )
        if path.is_symlink():
            raise CapabilityValidationError(f"Capability path is a symbolic link: {path.name}")
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise CapabilityValidationError(f"Capability does not exist: {capability_id}") from exc
        except OSError as exc:
            raise CapabilityValidationError(
                f"Unable to delete capability: {capability_id}"
            ) from exc

    def _read(self, path: Path) -> CapabilityDefinition:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise CapabilityValidationError(f"Unable to read capability: {path.name}") from exc
        return _parse_capability(content, self._display_path(path))

    def _display_path(self, path: Path) -> Path:
        try:
            return path.resolve().relative_to(self.layout.root)
        except ValueError as exc:
            raise CapabilityValidationError(
                "Capability path must stay inside the Workspace."
            ) from exc

    def _absolute_path(self, display_path: Path) -> Path:
        path = display_path if display_path.is_absolute() else self.layout.root / display_path
        try:
            path.resolve().relative_to(self.layout.root)
        except ValueError as exc:
            raise CapabilityValidationError(
                "Capability path must stay inside the Workspace."
            ) from exc
        return path

    def _find_definition(self, capability_id: str | None) -> CapabilityDefinition | None:
        if capability_id is None:
            return None
        matches = tuple(
            item for item in self.discover().definitions if item.capability_id == capability_id
        )
        if len(matches) > 1:
            raise CapabilityValidationError(f"duplicate capability id: {capability_id}")
        return matches[0] if matches else None

    def _path_for_id(self, capability_id: str | None) -> Path:
        normalized = str(capability_id or "").strip()
        if not _CAPABILITY_ID_RE.fullmatch(normalized):
            raise CapabilityValidationError(
                "Capability ID must use lowercase letters, numbers, '.', '_' or '-'."
            )
        directory = self.layout.capabilities_dir
        path = directory / f"{normalized}{_CAPABILITY_SUFFIX}"
        try:
            path.resolve().relative_to(self.layout.root)
        except ValueError as exc:
            raise CapabilityValidationError(
                "Capability path must stay inside the Workspace."
            ) from exc
        return path

    def _path_for_name(self, capability_name: str) -> Path:
        normalized = str(capability_name).strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or Path(normalized).name != normalized
            or any(character in normalized for character in "\\/\0\r\n")
        ):
            raise CapabilityValidationError("Capability path must stay inside the Workspace.")
        path = self.layout.capabilities_dir / f"{normalized}{_CAPABILITY_SUFFIX}"
        try:
            path.resolve().relative_to(self.layout.root)
        except ValueError as exc:
            raise CapabilityValidationError(
                "Capability path must stay inside the Workspace."
            ) from exc
        return path

    def _ensure_directory(self) -> None:
        directory = self.layout.capabilities_dir
        if directory.exists() and (not directory.is_dir() or directory.is_symlink()):
            raise CapabilityValidationError("Capability directory is not a regular directory.")
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CapabilityValidationError(
                "Unable to create the Workspace capability directory."
            ) from exc


def _parse_capability(
    content: str,
    path: Path | None,
) -> CapabilityDefinition:
    if not content.strip():
        raise CapabilityValidationError("Capability content must not be empty.")
    lines = content.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
    if not lines or lines[0].strip() != _CAPABILITY_DELIMITER:
        raise CapabilityValidationError("Capability must start with TOML frontmatter.")
    closing_index = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == _CAPABILITY_DELIMITER),
        None,
    )
    if closing_index is None:
        raise CapabilityValidationError("Capability frontmatter is not closed.")
    header = "".join(lines[1:closing_index])
    body = "".join(lines[closing_index + 1 :]).strip()
    try:
        payload = tomllib.loads(header)
    except tomllib.TOMLDecodeError as exc:
        raise CapabilityValidationError("Capability frontmatter is invalid TOML.") from exc
    capability_id = _required_text(payload.get("id"), "id")
    if _CAPABILITY_ID_RE.fullmatch(capability_id) is None:
        raise CapabilityValidationError(
            "Capability id must use lowercase letters, numbers, '.', '_' or '-'."
        )
    name = _required_text(payload.get("name"), "name")
    brief = _required_text(payload.get("brief"), "brief")
    enabled = payload.get("enabled", True)
    if not isinstance(enabled, bool):
        raise CapabilityValidationError("Capability enabled must be boolean.")
    if not body:
        raise CapabilityValidationError("Capability detail must not be empty.")
    if path is None:
        path = Path(f"{capability_id}{_CAPABILITY_SUFFIX}")
    return CapabilityDefinition(
        capability_id=capability_id,
        name=name,
        enabled=enabled,
        brief=brief,
        path=path,
        content=content,
        body=body,
    )


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityValidationError(f"Capability {field_name} must be a non-empty string.")
    normalized = value.strip()
    if any(character in normalized for character in "\r\n\0"):
        raise CapabilityValidationError(
            f"Capability {field_name} must not contain control characters."
        )
    return normalized


def _duplicate_ids(definitions: list[CapabilityDefinition]) -> set[str]:
    counts: dict[str, int] = {}
    for definition in definitions:
        counts[definition.capability_id] = counts.get(definition.capability_id, 0) + 1
    return {capability_id for capability_id, count in counts.items() if count > 1}


def _atomic_write(path: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    except OSError as exc:
        raise CapabilityValidationError(f"Unable to write capability: {path.name}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
