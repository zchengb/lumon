"""MCP configuration stays scoped, concurrency-safe and free of credential output."""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from lumon.errors import AgentRuntimeError, InvalidInputError, PreflightError
from lumon.tools.codex_mcp import CodexMcpManager, McpNewServer
from lumon.tools.codex_rpc import CodexRpc


class FakeRpc(CodexRpc):
    def __init__(self) -> None:
        super().__init__()
        self.writes: list[dict[str, object]] = []
        self.version = "v1"
        self.write_status = "ok"
        self.project_servers: dict[str, object] = {"project": {"command": "private-command"}}
        self.discovery: dict[str, object] = {
            "data": [
                {
                    "name": "figma",
                    "authStatus": "oAuth",
                    "runtimeStatus": None,
                    "tools": {"read_design": {}, "read_context": {}},
                    "toolsError": None,
                    "serverInfo": {"description": "  Official\nserver description.  "},
                }
            ],
            "nextCursor": None,
        }

    async def start(
        self, binary: str, workspace: Path, environment: Mapping[str, str] | None
    ) -> None:
        del binary, workspace, environment

    async def send(self, payload: dict[str, object]) -> None:
        del payload

    async def request(
        self, method: str, params: dict[str, object], *, timeout: float = 30
    ) -> dict[str, object]:
        del timeout
        if method == "initialize":
            return {}
        if method == "config/read":
            return {
                "layers": [
                    {
                        "name": {"type": "user"},
                        "version": self.version,
                        "config": {"mcp_servers": {"figma": {"env": {"TOKEN": "private-secret"}}}},
                    },
                    {
                        "name": {"type": "project"},
                        "version": "p1",
                        "config": {"mcp_servers": self.project_servers},
                    },
                ]
            }
        if method == "config/value/write":
            self.writes.append(params)
            return {"status": self.write_status}
        if method == "mcpServerStatus/list":
            return self.discovery
        raise AssertionError(method)

    async def close(self, *, kill_tools: bool = True) -> None:
        del kill_tools


@pytest.fixture
def mcp_manager(tmp_path: Path) -> tuple[CodexMcpManager, FakeRpc]:
    payload = [
        {
            "name": "figma",
            "enabled": True,
            "auth_status": "unknown",
            "transport": {"type": "streamable_http", "url": "https://mcp.figma.com/private-token"},
        },
        {
            "name": "project",
            "enabled": False,
            "auth_status": "unsupported",
            "transport": {"type": "stdio", "command": "private-command"},
        },
        {
            "name": "plugin",
            "enabled": True,
            "auth_status": "unsupported",
            "transport": {"type": "stdio"},
        },
    ]
    script = tmp_path / "codex"
    script.write_text(f"#!{sys.executable}\nprint({json.dumps(json.dumps(payload))})\n")
    script.chmod(0o700)
    rpc = FakeRpc()
    return CodexMcpManager(binary=str(script), rpc_factory=lambda: rpc), rpc


def test_inventory_preserves_scopes_and_never_returns_credentials(
    mcp_manager: tuple[CodexMcpManager, FakeRpc], tmp_path: Path
) -> None:
    manager, _ = mcp_manager
    inventory = asyncio.run(manager.list_servers(tmp_path))
    assert inventory.user_version == "v1"
    assert [(item.name, item.source, item.manageable) for item in inventory.servers] == [
        ("figma", "user", True),
        ("project", "project", False),
        ("plugin", "other", False),
    ]
    assert inventory.servers[0].description_kind == "figma"
    assert inventory.servers[2].description_kind is None
    assert "private" not in repr(inventory)


def test_official_descriptions_follow_implementation_not_server_name(tmp_path: Path) -> None:
    entries = [
        ("figma", {"type": "streamable_http", "url": "https://not-figma.example/mcp"}, None),
        ("custom-name", {"type": "streamable_http", "url": "https://mcp.figma.com/mcp"}, "figma"),
        ("one", {"type": "stdio", "command": "/bin/node_repl"}, "node_repl"),
        ("two", {"type": "stdio", "command": "/bin/SkyComputerUseClient"}, "computer_use"),
        ("three", {"type": "stdio", "command": "/bin/launch_codex_app_tools_mcp"}, "codex_app"),
        (
            "four",
            {
                "type": "stdio",
                "command": "/bin/node",
                "args": ["/lib/node_modules/@oai/cua-repl/bin/cua-repl.mjs"],
            },
            "cua_repl",
        ),
    ]
    payload = [
        {"name": name, "enabled": True, "transport": transport} for name, transport, _ in entries
    ]
    script = tmp_path / "codex"
    script.write_text(f"#!{sys.executable}\nprint({json.dumps(json.dumps(payload))})\n")
    script.chmod(0o700)
    manager = CodexMcpManager(binary=str(script), rpc_factory=FakeRpc)
    inventory = asyncio.run(manager.list_servers(tmp_path))
    assert [server.description_kind for server in inventory.servers] == [
        kind for _, _, kind in entries
    ]


def test_changes_use_version_and_preserve_external_sources(
    mcp_manager: tuple[CodexMcpManager, FakeRpc], tmp_path: Path
) -> None:
    manager, rpc = mcp_manager
    asyncio.run(manager.set_enabled(tmp_path, "figma", False, expected_version="v1"))
    assert rpc.writes[-1] == {
        "keyPath": "mcp_servers.figma.enabled",
        "value": False,
        "mergeStrategy": "replace",
        "expectedVersion": "v1",
    }
    asyncio.run(manager.remove(tmp_path, "figma", expected_version="v1"))
    assert rpc.writes[-1]["keyPath"] == "mcp_servers.figma"
    assert rpc.writes[-1]["value"] is None
    count = len(rpc.writes)
    with pytest.raises(PreflightError):
        asyncio.run(manager.set_enabled(tmp_path, "project", True, expected_version="v1"))
    with pytest.raises(PreflightError):
        asyncio.run(manager.remove(tmp_path, "figma", expected_version="stale"))
    assert len(rpc.writes) == count


def test_add_validates_input_and_rejects_duplicates(
    mcp_manager: tuple[CodexMcpManager, FakeRpc], tmp_path: Path
) -> None:
    manager, rpc = mcp_manager
    server = McpNewServer(
        "docs", "http", url="https://example.com/mcp", bearer_token_env_var="MCP_TOKEN"
    )
    asyncio.run(manager.add(tmp_path, server, expected_version="v1"))
    assert rpc.writes[-1]["value"] == {
        "url": "https://example.com/mcp",
        "bearer_token_env_var": "MCP_TOKEN",
    }
    with pytest.raises(PreflightError):
        asyncio.run(
            manager.add(
                tmp_path,
                McpNewServer("figma", "http", url="https://example.com"),
                expected_version="v1",
            )
        )
    with pytest.raises(InvalidInputError):
        asyncio.run(
            manager.add(
                tmp_path,
                McpNewServer("docs", "http", url="https://example.com/?token=secret"),
                expected_version="v1",
            )
        )


def test_user_server_overridden_by_project_is_read_only(
    mcp_manager: tuple[CodexMcpManager, FakeRpc], tmp_path: Path
) -> None:
    manager, rpc = mcp_manager
    rpc.project_servers["figma"] = {"url": "https://example.com/mcp"}
    inventory = asyncio.run(manager.list_servers(tmp_path))
    figma = next(server for server in inventory.servers if server.name == "figma")
    assert figma.source == "project"
    assert not figma.manageable
    with pytest.raises(PreflightError):
        asyncio.run(manager.remove(tmp_path, "figma", expected_version="v1"))
    assert not rpc.writes


def test_discovery_distinguishes_catalog_from_runtime_and_redacts_failure(
    mcp_manager: tuple[CodexMcpManager, FakeRpc], tmp_path: Path
) -> None:
    manager, rpc = mcp_manager
    result = asyncio.run(manager.discover(tmp_path, "figma"))
    assert result.tools == ("read_context", "read_design")
    assert result.runtime_status is None
    assert result.description == "Official server description."
    rpc.discovery = {
        "data": [
            {"name": "figma", "authStatus": "unknown", "tools": {}, "toolsError": "private-secret"}
        ]
    }
    failed = asyncio.run(manager.discover(tmp_path, "figma"))
    assert failed.failed
    assert "private-secret" not in repr(failed)
    rpc.discovery = {"data": "invalid"}
    with pytest.raises(AgentRuntimeError):
        asyncio.run(manager.discover(tmp_path, "figma"))


def test_reports_overridden_write(
    mcp_manager: tuple[CodexMcpManager, FakeRpc], tmp_path: Path
) -> None:
    manager, rpc = mcp_manager
    rpc.write_status = "okOverridden"
    with pytest.raises(PreflightError, match="saved but is overridden"):
        asyncio.run(manager.set_enabled(tmp_path, "figma", False, expected_version="v1"))
