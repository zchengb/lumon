"""Workspace context seam for native Harness sessions.

Native providers read this small, provider-neutral context. Legacy transport
instructions are deliberately kept out of the native world; they remain
available only when a workspace explicitly opts into compatibility mode.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from agents.runtime.harness import native_runtime_configured


_LEGACY_FILES = (
    "action-catalog.md",
    "protocol.md",
    "blacklist.md",
)
_LEGACY_RESPONSIBILITY_FILES = {
    "blacklist.md",
    "dylan-workflow.md",
    "irving-workflow.md",
    "mark-workflow.md",
    "milchick-workflow.md",
}


def native_context_enabled(workspace: Path) -> bool:
    root = Path(workspace).expanduser().resolve()
    common_path = root / "config" / "common.json"
    try:
        common = json.loads(common_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        common = {}
    if native_runtime_configured(common):
        return True
    # A provider-only disposable workspace has no common.json. Native is the
    # safe default there; legacy mode must be an explicit operator choice.
    return os.environ.get("LUMON_LEGACY_RUNTIME", "").strip().casefold() not in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def _copy(package_agents: Path, target: Path, source_name: str, destination_name: str | None = None) -> None:
    source = package_agents / source_name
    destination = target / (destination_name or source_name)
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def ensure_workspace_context(workspace: Path, *, agent_id: str = "") -> None:
    root = Path(workspace).expanduser().resolve()
    target = root / ".lumon"
    target.mkdir(parents=True, exist_ok=True)
    package_agents = Path(__file__).resolve().parents[1]

    if native_context_enabled(root):
        # Remove only generated transport files. This is intentionally scoped
        # to .lumon and lets user-authored workspace material remain intact.
        for name in _LEGACY_FILES:
            path = target / name
            path.unlink(missing_ok=True)
        responsibilities = target / "responsibilities"
        for name in _LEGACY_RESPONSIBILITY_FILES:
            (responsibilities / name).unlink(missing_ok=True)
        _copy(package_agents, target, "native-protocol.md")
        _copy(package_agents, target, "connected-tools.md")
        if agent_id:
            _copy(package_agents, target, f"responsibilities/{agent_id}.md", f"responsibilities/{agent_id}.md")
        if agent_id == "milchick":
            _copy(package_agents, target, "milchick/soul.md", "milchick-soul.md")
        from agents.security.tools import write_host_tool_manifest

        write_host_tool_manifest(root)
        return

    # Explicit compatibility mode preserves the pre-native contract for
    # migrated workspaces and third-party callers.
    _copy(package_agents, target, "action-catalog.md")
    _copy(package_agents, target, "protocol.md")
    _copy(package_agents, target, "native-protocol.md")
    _copy(package_agents, target, "connected-tools.md")
    _copy(package_agents, target, "responsibilities/blacklist.md", "blacklist.md")
    if agent_id:
        _copy(package_agents, target, f"responsibilities/{agent_id}.md", f"responsibilities/{agent_id}.md")
        _copy(package_agents, target, f"responsibilities/{agent_id}-workflow.md", f"responsibilities/{agent_id}-workflow.md")
    if agent_id == "milchick":
        _copy(package_agents, target, "milchick/soul.md", "milchick-soul.md")
    from agents.security.tools import write_host_tool_manifest

    write_host_tool_manifest(root)
