"""Dynamic Host Tool registry exposed at the Harness seam."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
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
        if not include_legacy and action.startswith("agent.job."):
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
    """Write the current registry into the disposable workspace context."""
    target = Path(workspace).expanduser().resolve() / ".lumon" / "host-tools.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "version": 1,
                "protocol": "native-first-action-request",
                "tools": host_tool_manifest(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target
