"""Read and write the small, inspectable Workspace TOML configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from lumon.errors import PreflightError
from lumon.workspace.model import RepositoryRecord

WORKSPACE_CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class WorkspaceConfig:
    """Workspace-owned configuration and its registered Repositories."""

    name: str
    repositories: tuple[RepositoryRecord, ...] = ()
    schema_version: int = WORKSPACE_CONFIG_SCHEMA_VERSION

    def write(self, path: Path) -> None:
        """Write a deterministic TOML representation to ``path``."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render(self), encoding="utf-8")


def load_workspace_config(path: Path) -> WorkspaceConfig:
    """Load and validate a Workspace configuration without accepting loose dicts."""

    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise PreflightError(f"Unable to read Workspace configuration: {path}") from exc

    schema_version = payload.get("schema_version")
    name = payload.get("name")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != WORKSPACE_CONFIG_SCHEMA_VERSION
    ):
        raise PreflightError(f"Unsupported Workspace configuration schema at {path}")
    if not isinstance(name, str) or not name.strip():
        raise PreflightError(f"Workspace configuration has an invalid name: {path}")

    raw_repositories: object = payload.get("repositories", [])
    if not isinstance(raw_repositories, list):
        raise PreflightError(f"Workspace repositories must be an array: {path}")

    repositories: list[RepositoryRecord] = []
    names: set[str] = set()
    for index, raw_repository in enumerate(cast(list[object], raw_repositories)):
        if not isinstance(raw_repository, dict):
            raise PreflightError(f"Invalid Repository at index {index}: {path}")
        repository = _parse_repository(cast(dict[str, object], raw_repository), path, index)
        if repository.name in names:
            raise PreflightError(f"Duplicate Repository name '{repository.name}': {path}")
        names.add(repository.name)
        repositories.append(repository)

    return WorkspaceConfig(
        name=name, repositories=tuple(repositories), schema_version=schema_version
    )


def _parse_repository(value: dict[str, object], source: Path, index: int) -> RepositoryRecord:
    name = value.get("name")
    url = value.get("url")
    path = value.get("path")
    branch = value.get("branch")
    revision = value.get("revision")
    if not all(
        isinstance(item, str) and item.strip() for item in (name, url, path, branch, revision)
    ):
        raise PreflightError(f"Invalid Repository fields at index {index}: {source}")

    assert isinstance(name, str)
    assert isinstance(url, str)
    assert isinstance(path, str)
    assert isinstance(branch, str)
    assert isinstance(revision, str)
    if (
        name in {".", ".."}
        or any(character in name for character in "/\\\0")
        or name.strip() != name
    ):
        raise PreflightError(f"Invalid Repository name at index {index}: {source}")
    relative_path = Path(path)
    expected_path = Path("repos") / name
    if relative_path.is_absolute() or relative_path != expected_path:
        raise PreflightError(f"Repository path must be repos/{name}: {source}")

    return RepositoryRecord(
        name=name,
        url=url,
        path=path,
        branch=branch,
        revision=revision,
    )


def _render(config: WorkspaceConfig) -> str:
    lines = [
        f"schema_version = {config.schema_version}",
        f"name = {_toml_string(config.name)}",
    ]
    for repository in config.repositories:
        lines.extend(
            [
                "",
                "[[repositories]]",
                f"name = {_toml_string(repository.name)}",
                f"url = {_toml_string(repository.url)}",
                f"path = {_toml_string(repository.path)}",
                f"branch = {_toml_string(repository.branch)}",
                f"revision = {_toml_string(repository.revision)}",
            ]
        )
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
