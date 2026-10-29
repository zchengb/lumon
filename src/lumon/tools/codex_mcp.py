"""Manage display-safe Codex MCP settings without starting an Agent turn."""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncGenerator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from lumon.errors import AgentRuntimeError, InvalidInputError, PreflightError
from lumon.tools.codex import resolve_codex_binary
from lumon.tools.codex_rpc import CodexRpc, CodexRpcError
from lumon.tools.github_mcp_proxy import (
    github_server_name,
    workspace_github_hosts,
    workspace_mcp_config,
)
from lumon.version import __version__

_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
McpTransport = Literal["stdio", "http", "unknown"]
McpSource = Literal["user", "project", "other", "workspace"]
McpDescriptionKind = Literal["figma", "codex_app", "computer_use", "cua_repl", "node_repl"]


@dataclass(frozen=True, slots=True)
class McpServer:
    name: str
    enabled: bool
    transport: McpTransport
    auth_status: str
    source: McpSource
    manageable: bool
    description_kind: McpDescriptionKind | None = None
    workspace_host: str | None = None


@dataclass(frozen=True, slots=True)
class McpInventory:
    servers: tuple[McpServer, ...]
    user_version: str | None


@dataclass(frozen=True, slots=True)
class McpDiscovery:
    auth_status: str
    runtime_status: str | None
    tools: tuple[str, ...]
    failed: bool
    total_tools: int
    description: str | None = None


@dataclass(frozen=True, slots=True)
class McpNewServer:
    name: str
    transport: Literal["stdio", "http"]
    command: str | None = None
    args: tuple[str, ...] = ()
    url: str | None = None
    bearer_token_env_var: str | None = None


class _Transport(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    type: str = "unknown"
    command: str | None = None
    args: list[str] = Field(default_factory=list, max_length=128)
    url: str | None = None


class _ListedServer(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    name: str = Field(min_length=1, max_length=256)
    enabled: bool
    auth_status: str = Field(default="unknown", max_length=64)
    transport: _Transport = Field(default_factory=_Transport)


class _LayerName(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    type: str


class _Layer(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    name: _LayerName
    version: str
    config: dict[str, object] = Field(default_factory=dict)


class _ConfigRead(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    layers: list[_Layer]


class _ServerInfo(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    description: str | None = None


class _DiscoveryServer(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    name: str
    auth_status: str = Field(default="unknown", alias="authStatus")
    runtime_status: str | None = Field(default=None, alias="runtimeStatus")
    tools: dict[str, object] = Field(default_factory=dict)
    tools_error: str | None = Field(default=None, alias="toolsError")
    server_info: _ServerInfo | None = Field(default=None, alias="serverInfo")


class _DiscoveryPage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    data: list[_DiscoveryServer]


class CodexMcpManager:
    """Read the effective Workspace catalog and edit only the user config layer."""

    def __init__(
        self,
        binary: str | None = None,
        *,
        environment: Mapping[str, str] | None = None,
        rpc_factory: Callable[[], CodexRpc] = CodexRpc,
    ) -> None:
        self.binary = binary or resolve_codex_binary()
        self.environment = dict(environment) if environment is not None else None
        self._rpc_factory = rpc_factory
        self._write_lock = asyncio.Lock()

    async def list_servers(self, workspace: Path) -> McpInventory:
        """Return names and configuration state, never command arguments or secrets."""
        listed = await self._list_cli(workspace)
        async with self._rpc(workspace) as rpc:
            layers = await self._read_layers(rpc, workspace)
        return _inventory(listed, layers, _workspace_hosts(workspace))

    async def discover(self, workspace: Path, name: str) -> McpDiscovery:
        """Request one server's tool catalog; runtime state may remain unknown."""
        inventory = await self.list_servers(workspace)
        server = next((item for item in inventory.servers if item.name == name), None)
        if server is None or not server.enabled:
            raise PreflightError("MCP server is unavailable or disabled. Refresh and try again.")
        async with self._rpc(workspace) as rpc:
            result = await rpc.request(
                "mcpServerStatus/list",
                {"serverName": name, "detail": "full", "limit": 1},
                timeout=30,
            )
        return _discovery(result, name)

    async def add(
        self, workspace: Path, server: McpNewServer, *, expected_version: str | None
    ) -> None:
        value = _new_server_value(server)
        async with self._write_lock, self._rpc(workspace) as rpc:
            inventory = _inventory(
                await self._list_cli(workspace),
                await self._read_layers(rpc, workspace),
                _workspace_hosts(workspace),
            )
            _require_version(inventory, expected_version)
            if any(item.name == server.name for item in inventory.servers):
                raise PreflightError("MCP server already exists. Refresh and try again.")
            await _write(rpc, f"mcp_servers.{server.name}", value, expected_version)

    async def set_enabled(
        self, workspace: Path, name: str, enabled: bool, *, expected_version: str | None
    ) -> None:
        await self._change(workspace, name, enabled, expected_version, remove=False)

    async def remove(self, workspace: Path, name: str, *, expected_version: str | None) -> None:
        await self._change(workspace, name, None, expected_version, remove=True)

    async def _change(
        self,
        workspace: Path,
        name: str,
        value: bool | None,
        expected_version: str | None,
        *,
        remove: bool,
    ) -> None:
        if not _NAME.fullmatch(name):
            raise InvalidInputError("Invalid MCP server name.")
        async with self._write_lock, self._rpc(workspace) as rpc:
            inventory = _inventory(
                await self._list_cli(workspace),
                await self._read_layers(rpc, workspace),
                _workspace_hosts(workspace),
            )
            _require_version(inventory, expected_version)
            server = next((item for item in inventory.servers if item.name == name), None)
            if server is None or not server.manageable:
                raise PreflightError("This MCP server is managed by another configuration layer.")
            key = f"mcp_servers.{name}" + ("" if remove else ".enabled")
            await _write(rpc, key, value, expected_version)

    async def _list_cli(self, workspace: Path) -> tuple[_ListedServer, ...]:
        try:
            process = await asyncio.create_subprocess_exec(
                self.binary,
                *(part for item in workspace_mcp_config(workspace) for part in ("--config", item)),
                "mcp",
                "list",
                "--json",
                cwd=workspace,
                env=self.environment,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=15)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            if process.returncode != 0 or len(stdout) > 2_000_000:
                raise ValueError("Invalid MCP catalog")
            try:
                payload = TypeAdapter(list[_ListedServer]).validate_json(stdout)
            except ValidationError:
                raise ValueError("Invalid MCP catalog") from None
            if len(payload) > 1000:
                raise ValueError("Invalid MCP catalog")
            return tuple(payload)
        except (OSError, TimeoutError, ValueError, ValidationError) as exc:
            raise AgentRuntimeError(
                "Could not read Codex MCP settings. Check the local Codex CLI."
            ) from exc

    @asynccontextmanager
    async def _rpc(self, workspace: Path) -> AsyncGenerator[CodexRpc]:
        rpc = self._rpc_factory()
        try:
            config = workspace_mcp_config(workspace)
            if config:
                await rpc.start(self.binary, workspace, self.environment, config=config)
            else:
                await rpc.start(self.binary, workspace, self.environment)
            await rpc.request(
                "initialize",
                {"clientInfo": {"name": "lumon", "title": "Lumon", "version": __version__}},
                timeout=15,
            )
            await rpc.send({"method": "initialized"})
            yield rpc
        except (OSError, TimeoutError, CodexRpcError, ValidationError, ValueError) as exc:
            raise AgentRuntimeError(
                "Codex MCP operation failed. Refresh and check the local Codex CLI."
            ) from exc
        finally:
            await rpc.close()

    async def _read_layers(self, rpc: CodexRpc, workspace: Path) -> tuple[_Layer, ...]:
        response = await rpc.request(
            "config/read", {"cwd": str(workspace), "includeLayers": True}, timeout=15
        )
        try:
            return tuple(_ConfigRead.model_validate(response).layers)
        except ValidationError:
            raise ValueError("Invalid MCP configuration layers") from None


def _workspace_hosts(workspace: Path) -> dict[str, str]:
    return {github_server_name(host): host for host in workspace_github_hosts(workspace)}


def _inventory(
    listed: tuple[_ListedServer, ...],
    layers: tuple[_Layer, ...],
    workspace_hosts: Mapping[str, str],
) -> McpInventory:
    user = next((layer for layer in layers if layer.name.type == "user"), None)
    user_names: set[str] = _layer_names(user) if user else set()
    other_names = {
        name for layer in layers if layer.name.type != "user" for name in _layer_names(layer)
    }
    project_names = {
        name for layer in layers if layer.name.type == "project" for name in _layer_names(layer)
    }
    servers: list[McpServer] = []
    for item in listed:
        host = workspace_hosts.get(item.name)
        source: McpSource = "other"
        if host is not None:
            source = "workspace"
        elif item.name in project_names:
            source = "project"
        elif item.name in user_names:
            source = "user"
        transport: McpTransport = (
            "stdio"
            if item.transport.type == "stdio"
            else "http"
            if item.transport.type == "streamable_http"
            else "unknown"
        )
        servers.append(
            McpServer(
                item.name,
                item.enabled,
                transport,
                _auth(item.auth_status),
                source,
                bool(
                    host is None
                    and user
                    and item.name in user_names
                    and item.name not in other_names
                    and _NAME.fullmatch(item.name)
                ),
                _description_kind(item.transport),
                host,
            )
        )
    return McpInventory(tuple(servers), user.version if user else None)


def _description_kind(transport: _Transport) -> McpDescriptionKind | None:
    # Match known implementations, never a user-chosen server name alone.
    if transport.type == "streamable_http" and transport.url:
        try:
            url = urlsplit(transport.url)
            if url.scheme == "https" and url.hostname == "mcp.figma.com":
                return "figma"
        except ValueError:
            return None
    if transport.type != "stdio" or not transport.command:
        return None
    command = Path(transport.command).name
    if command == "launch_codex_app_tools_mcp":
        return "codex_app"
    if command == "SkyComputerUseClient":
        return "computer_use"
    if command == "node_repl":
        return "node_repl"
    if command == "node" and any(
        arg.replace("\\", "/").endswith("/node_modules/@oai/cua-repl/bin/cua-repl.mjs")
        for arg in transport.args
    ):
        return "cua_repl"
    return None


def _layer_names(layer: _Layer) -> set[str]:
    try:
        servers = TypeAdapter(dict[str, object]).validate_python(
            layer.config.get("mcp_servers", {})
        )
    except ValidationError:
        raise AgentRuntimeError("Could not read Codex MCP configuration layers.") from None
    return set(servers)


def _auth(value: str) -> str:
    return (
        value
        if value
        in {
            "unknown",
            "unsupported",
            "notLoggedIn",
            "not_logged_in",
            "bearerToken",
            "bearer_token",
            "oAuth",
            "oauth",
        }
        else "unknown"
    )


def _require_version(inventory: McpInventory, expected: str | None) -> None:
    if not expected or inventory.user_version != expected:
        raise PreflightError("MCP settings changed or cannot be managed. Refresh and try again.")


def _new_server_value(server: McpNewServer) -> dict[str, object]:
    if not _NAME.fullmatch(server.name):
        raise InvalidInputError("Invalid MCP server name.")
    if server.transport == "stdio":
        if (
            not server.command
            or not server.command.strip()
            or len(server.command) > 4096
            or len(server.args) > 64
            or any(len(arg) > 4096 for arg in server.args)
        ):
            raise InvalidInputError("Provide a valid MCP command and arguments.")
        return {"command": server.command.strip(), "args": list(server.args)}
    if not server.url or len(server.url) > 4096:
        raise InvalidInputError("Provide a valid MCP URL.")
    try:
        url = urlsplit(server.url)
        valid = (
            url.scheme in {"http", "https"}
            and bool(url.hostname)
            and (url.port is None or 1 <= url.port <= 65535)
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and not any(character.isspace() or ord(character) < 32 for character in server.url)
        )
    except ValueError:
        valid = False
    if not valid:
        raise InvalidInputError("MCP URL must use HTTP(S) without credentials, query, or fragment.")
    value: dict[str, object] = {"url": server.url}
    if server.bearer_token_env_var:
        if not _ENV_NAME.fullmatch(server.bearer_token_env_var):
            raise InvalidInputError("Invalid bearer-token environment variable name.")
        value["bearer_token_env_var"] = server.bearer_token_env_var
    return value


async def _write(rpc: CodexRpc, key: str, value: object, version: str | None) -> None:
    response = await rpc.request(
        "config/value/write",
        {"keyPath": key, "value": value, "mergeStrategy": "replace", "expectedVersion": version},
        timeout=15,
    )
    if response.get("status") != "ok":
        raise PreflightError(
            "MCP setting was saved but is overridden by another configuration layer."
        )


def _discovery(result: dict[str, object], name: str) -> McpDiscovery:
    try:
        page = _DiscoveryPage.model_validate(result)
    except ValidationError:
        raise AgentRuntimeError("Codex returned an invalid MCP discovery result.") from None
    item = next((entry for entry in page.data if entry.name == name), None)
    if item is None:
        raise PreflightError("MCP server could not be discovered. Refresh and try again.")
    tools = tuple(sorted(key for key in item.tools if len(key) <= 256))
    runtime = item.runtime_status
    description = (
        " ".join(item.server_info.description.split())
        if item.server_info and item.server_info.description
        else ""
    )
    if len(description) > 240:
        description = description[:237].rstrip() + "..."
    return McpDiscovery(
        _auth(item.auth_status),
        runtime
        if runtime is not None
        and runtime
        in {
            "notStarted",
            "starting",
            "connected",
            "authenticationRequired",
            "failed",
            "cancelled",
            "disabled",
        }
        else None,
        tools[:200],
        bool(item.tools_error) or runtime in {"failed", "cancelled", "authenticationRequired"},
        len(item.tools),
        description or None,
    )
