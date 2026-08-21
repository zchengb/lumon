"""Dynamic Host Tool registry exposed at the Harness seam."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import shutil
from pathlib import Path
from typing import Any

from agents.security.actions import ALL_ACTIONS, MUTATION_ACTIONS


@dataclass(frozen=True)
class HostToolSpec:
    name: str
    description: str
    schema: dict[str, Any]
    risk_level: str
    default_owner: str
    authorization_class: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_OWNERS = {
    "risk": "dylan",
    "scan": "dylan",
    "delivery": "mark",
    "loop": "mark",
    "story": "mark",
    "technical_plan": "mark",
    "test_case": "mark",
    "agent": "milchick",
    "project": "milchick",
    "workflow": "milchick",
    "schedule": "milchick",
    "lumen": "milchick",
    "jira": "milchick",
    "feishu": "current_agent",
}

_REQUIRED = {
    "delivery.start": ["story"],
    "delivery.cancel": ["run_id"],
    "delivery.quick_change": ["repository", "target_files", "request"],
    "loop.technical": ["issue_key"],
    "test_case.generate": ["scope"],
    "agent.delegate": ["target_agent", "capability"],
    "agent.job.create": ["target_agent", "capability"],
    "feishu.say": ["message"],
    "feishu.send_progress": ["message"],
    "feishu.send_file": ["path"],
    "jira.workitem.get": ["issue_key"],
    "jira.workitem.query": ["jql"],
    "jira.workitem.update": ["issue_key"],
}


def _owner(action: str) -> str:
    return _OWNERS.get(str(action).split(".", 1)[0], "current_agent")


def host_tool_specs(*, include_legacy: bool = True) -> list[HostToolSpec]:
    """Return the current catalog as small provider-readable tool schemas."""
    specs: list[HostToolSpec] = []
    for action in sorted(ALL_ACTIONS):
        # Native conversation removes the old per-turn delegation verbs, but
        # durable background work remains a legitimate native capability.
        # Keep only job creation in the compact native catalog; lifecycle
        # inspection/cancellation stays on the Host/dashboard surface.
        if not include_legacy and action.startswith("agent.job.") and action != "agent.job.create":
            continue
        required = list(_REQUIRED.get(action, []))
        properties = {
            field: {"type": "array" if field == "target_files" else "string"}
            for field in required
        }
        if action in {"risk.resolve", "risk.mark_remediated", "risk.reconcile"}:
            properties.setdefault("reason", {"type": "string"})
        specs.append(
            HostToolSpec(
                name=action,
                description=f"Host-mediated {action.replace('.', ' ')} action.",
                schema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": True,
                },
                risk_level="high" if action in MUTATION_ACTIONS else "low",
                default_owner=_owner(action),
                authorization_class="brokered_mutation" if action in MUTATION_ACTIONS else "brokered_read",
            )
        )
    return specs


def host_tool_manifest() -> list[dict[str, Any]]:
    return [item.to_dict() for item in host_tool_specs()]


def write_host_tool_manifest(workspace: Path) -> Path:
    """Write native connected-tool schemas into the disposable workspace.

    The legacy action catalog is retained in a separate field for fallback
    providers, but native Cursor/OpenCode/Codex sessions consume the registry
    directly and do not need to hand-build an envelope.
    """
    target = Path(workspace).expanduser().resolve() / ".lumon" / "host-tools.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    from agents.runtime.connected_tools import ConnectedToolRegistry

    legacy_enabled = True
    common_path = target.parent.parent / "config" / "common.json"
    try:
        common = json.loads(common_path.read_text(encoding="utf-8"))
        runtime = common.get("conversation") if isinstance(common, dict) else None
        if not isinstance(runtime, dict) and isinstance(common, dict):
            runtime = common.get("conversation_runtime")
        if isinstance(runtime, dict) and "legacy_compatibility" in runtime:
            legacy_enabled = str(runtime.get("legacy_compatibility")).strip().casefold() in {
                "1", "true", "yes", "on", "enabled"
            }
    except (OSError, TypeError, json.JSONDecodeError):
        pass

    target.write_text(
        json.dumps(
            {
                "version": 2,
                "protocol": "thread-native-connected-tools",
                "tools": ConnectedToolRegistry(include_legacy=False).schemas(),
                "legacy_compatibility": {
                    "enabled": legacy_enabled,
                    "protocol": "legacy-envelopes",
                    "tools": host_tool_manifest(),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    native_docs = Path(__file__).resolve().parents[1] / "connected-tools.md"
    if native_docs.is_file():
        shutil.copyfile(native_docs, target.parent / native_docs.name)
    native_protocol = Path(__file__).resolve().parents[1] / "native-protocol.md"
    if native_protocol.is_file():
        shutil.copyfile(native_protocol, target.parent / native_protocol.name)
    return target
