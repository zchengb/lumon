"""Read and write the small, inspectable Workspace TOML configuration."""

from __future__ import annotations

import re
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
        path.write_text(self.as_toml(), encoding="utf-8")

    def as_toml(self) -> str:
        """Return the deterministic Workspace representation."""

        return _render(self)


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
    mcp_server = value.get("mcp_server")
    auto_scan = value.get("auto_scan", True)
    auto_delivery = value.get("auto_delivery", True)
    if not all(isinstance(item, str) and item.strip() for item in (name, url, path, branch)):
        raise PreflightError(f"Invalid Repository fields at index {index}: {source}")

    assert isinstance(name, str)
    assert isinstance(url, str)
    assert isinstance(path, str)
    assert isinstance(branch, str)
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
    if mcp_server is not None and (
        not isinstance(mcp_server, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", mcp_server) is None
    ):
        raise PreflightError(f"Invalid Repository MCP source at index {index}: {source}")
    if not isinstance(auto_scan, bool) or not isinstance(auto_delivery, bool):
        raise PreflightError(f"Invalid Repository automation scope at index {index}: {source}")

    return RepositoryRecord(
        name=name,
        url=url,
        path=path,
        branch=branch,
        mcp_server=mcp_server,
        auto_scan=auto_scan,
        auto_delivery=auto_delivery,
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
            ]
        )
        if repository.mcp_server is not None:
            lines.append(f"mcp_server = {_toml_string(repository.mcp_server)}")
        if not repository.auto_scan:
            lines.append("auto_scan = false")
        if not repository.auto_delivery:
            lines.append("auto_delivery = false")
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
