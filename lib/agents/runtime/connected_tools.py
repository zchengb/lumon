"""Native Connected Tool registry and compatibility executor seam."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from agents.security.tools import HostToolSpec, host_tool_specs
from agents.security.trusted import TrustedActionContext, execute_trusted_actions


_NATIVE_ALIASES = {
    "jira.get": "jira.workitem.get",
    "jira.search": "jira.workitem.query",
    "jira.create": "jira.workitem.create",
    "jira.update": "jira.workitem.update",
    "feishu.file": "feishu.send_file",
    "agent.directory": "agent.list",
}

_LEGACY_CONVERSATION_TOOLS = frozenset(
    {
        "agent.delegate",
        "feishu.say",
        "feishu.send_progress",
        "feishu.send_file",
    }
)

_TRUSTED_IDENTITY_FIELDS = frozenset(
    {
        "actor_user_id",
        "actor",
        "chat_id",
        "thread_id",
        "source_message_id",
        "trace_id",
        "explicit_authorization",
        "agent_id",
        "project_slug",
        "chat_type",
        "workspace_path",
        "_workspace_path",
        "_root_id",
        "_origin_user_id",
        "_source_agent",
        "_target_agent",
        "_relay_id",
        "_relay_hop",
        "_relay_visited",
    }
)


@dataclass(frozen=True)
class ConnectedTool:
    name: str
    description: str
    schema: dict[str, Any]
    implementation: str
    risk_level: str = "low"
    default_owner: str = "current_agent"
    authorization_class: str = "brokered_read"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema,
            "risk_level": self.risk_level,
            "implementation": self.implementation,
            "default_owner": self.default_owner,
            "authorization_class": self.authorization_class,
        }


class ConnectedToolRegistry:
    """Expose provider-native schemas without teaching Agents envelope syntax."""

    def __init__(self, specs: Iterable[HostToolSpec] | None = None, *, include_legacy: bool = False) -> None:
        source = list(specs) if specs is not None else host_tool_specs(include_legacy=include_legacy)
        if not include_legacy:
            source = [item for item in source if item.name not in _LEGACY_CONVERSATION_TOOLS]
        self._tools: dict[str, ConnectedTool] = {}
        for item in source:
            self._tools[item.name] = ConnectedTool(
                name=item.name,
                description=item.description,
                schema=item.schema,
                implementation=item.name,
                risk_level=item.risk_level,
                default_owner=item.default_owner,
                authorization_class=item.authorization_class,
            )
        for alias, implementation in _NATIVE_ALIASES.items():
            if implementation in self._tools:
                source_spec = self._tools[implementation]
                self._tools[alias] = ConnectedTool(
                    name=alias,
                    description=source_spec.description.replace(implementation, alias),
                    schema=source_spec.schema,
                    implementation=implementation,
                    risk_level=source_spec.risk_level,
                    default_owner=source_spec.default_owner,
                    authorization_class=source_spec.authorization_class,
                )
        if "feishu.file" not in self._tools:
            self._tools["feishu.file"] = ConnectedTool(
                name="feishu.file",
                description="Upload and attach a workspace file to the current Feishu conversation.",
                schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "caption": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
                implementation="feishu.send_file",
                risk_level="low",
                default_owner="current_agent",
                authorization_class="brokered_read",
            )
        # These are real seams even when a workspace has not installed a
        # concrete Bitable adapter yet.  An injected executor can provide the
        # implementation without changing the Harness interface.
        for name in ("bitable.read", "bitable.write"):
            if name not in self._tools:
                self._tools[name] = ConnectedTool(
                    name=name,
                    description=f"Native {name.replace('.', ' ')} connected tool.",
                    schema={"type": "object", "properties": {}, "additionalProperties": True},
                    implementation=name,
                    risk_level="high" if name.endswith("write") else "low",
                    default_owner="current_agent",
                    authorization_class="brokered_mutation" if name.endswith("write") else "brokered_read",
                )

    def get(self, name: str) -> ConnectedTool | None:
        return self._tools.get(str(name or "").strip().casefold())

    def list(self) -> list[ConnectedTool]:
        return [self._tools[key] for key in sorted(self._tools)]

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.name,
                "description": item.description,
                "input_schema": item.schema,
                "risk_level": item.risk_level,
                "default_owner": item.default_owner,
                "authorization_class": item.authorization_class,
            }
            for item in self.list()
        ]


class ConnectedToolExecutor:
    """Execute a native call at the existing trusted Host seam.

    Native providers bypass XML parsing, but external effects still receive a
    Host-bound identity and receipt.  The executor may be injected for a
    first-class Bitable or provider-specific adapter.
    """

    def __init__(
        self,
        *,
        registry: ConnectedToolRegistry | None = None,
        native_executor: Callable[[str, dict[str, Any], TrustedActionContext], Any] | None = None,
    ) -> None:
        self.registry = registry or ConnectedToolRegistry()
        self.native_executor = native_executor

    def execute(
        self,
        name: str,
        arguments: Mapping[str, Any] | None,
        *,
        context: TrustedActionContext,
    ) -> Any:
        tool = self.registry.get(name)
        if tool is None:
            raise KeyError(f"unknown connected tool: {name}")
        args = dict(arguments or {})
        for field in _TRUSTED_IDENTITY_FIELDS:
            args.pop(field, None)
        if self.native_executor is not None:
            return self.native_executor(tool.implementation, args, context)
        receipts = execute_trusted_actions(
            context=context,
            requests=[{"action": tool.implementation, "arguments": args, "resource": {}}],
        )
        return receipts[0] if receipts else None

    def execute_many(
        self,
        calls: Iterable[Mapping[str, Any]],
        *,
        context: TrustedActionContext,
    ) -> list[Any]:
        """Execute a provider-native batch while preserving call order."""

        results: list[Any] = []
        for call in calls:
            if not isinstance(call, Mapping):
                continue
            name = str(call.get("name") or call.get("tool") or "").strip()
            arguments = call.get("arguments") if isinstance(call.get("arguments"), Mapping) else {}
            results.append(self.execute(name, arguments, context=context))
        return results
