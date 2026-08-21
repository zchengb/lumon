"""Provider-native connected-tool registration.

The registry is the one tool interface shared by Cursor, OpenCode and Codex.
This module materializes provider-neutral MCP metadata inside the Agent World
and provides a small JSON-RPC server entry point for providers that support
stdio MCP.  Legacy text envelopes remain a compatibility adapter only.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any, Mapping

from agents.runtime.connected_tools import ConnectedToolRegistry


NATIVE_TOOL_PROTOCOL = "lumon-native-tools/1"


def native_tool_manifest(*, provider: str = "", server_command: str = "") -> dict[str, Any]:
    python_executable = str(sys.executable or "python3")
    command = server_command or shlex.join([python_executable, "-m", "agents.runtime.native_tool_server"])
    registry = ConnectedToolRegistry(include_legacy=False)
    tools = registry.schemas()
    return {
        "version": 1,
        "protocol": NATIVE_TOOL_PROTOCOL,
        "provider": str(provider or "").strip().casefold(),
        "server": {"name": "lumon", "transport": "stdio", "command": command},
        "tools": tools,
    }


def write_native_tool_manifests(workspace: Path, *, provider: str = "") -> tuple[Path, Path]:
    root = Path(workspace).expanduser().resolve() / ".lumon"
    root.mkdir(parents=True, exist_ok=True)
    python_executable = str(sys.executable or "python3")
    payload = native_tool_manifest(provider=provider)
    manifest_path = root / "native-tools.json"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The shape is intentionally close to the common MCP config used by the
    # provider CLIs. Providers may copy/translate this file into their own
    # config without changing the connected-tool interface.
    mcp_path = root / "mcp.json"
    mcp_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "lumon": {
                        "command": python_executable,
                        "args": ["-m", "agents.runtime.native_tool_server"],
                        "env": {"LUMON_NATIVE_TOOL_MANIFEST": str(manifest_path)},
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    # Cursor discovers project MCP servers from .cursor/mcp.json. Keep the
    # provider-facing file inside the disposable workspace; the Host socket
    # and entry-gate environment are inherited only for this process tree.
    cursor_mcp = Path(workspace).expanduser().resolve() / ".cursor" / "mcp.json"
    cursor_mcp.parent.mkdir(parents=True, exist_ok=True)
    cursor_mcp.write_text(mcp_path.read_text(encoding="utf-8"), encoding="utf-8")
    opencode_mcp = Path(workspace).expanduser().resolve() / ".opencode" / "mcp.json"
    opencode_mcp.parent.mkdir(parents=True, exist_ok=True)
    opencode_mcp.write_text(mcp_path.read_text(encoding="utf-8"), encoding="utf-8")
    return manifest_path, mcp_path


def load_native_tool_manifest(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def mcp_tools_list(path: str | Path | None = None) -> list[dict[str, Any]]:
    manifest = load_native_tool_manifest(path or "") if path else native_tool_manifest()
    tools = manifest.get("tools") if isinstance(manifest.get("tools"), list) else []
    return [item for item in tools if isinstance(item, dict)]


__all__ = [
    "NATIVE_TOOL_PROTOCOL",
    "load_native_tool_manifest",
    "mcp_tools_list",
    "native_tool_manifest",
    "write_native_tool_manifests",
]
