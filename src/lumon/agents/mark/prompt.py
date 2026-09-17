"""Render Mark's packaged Workspace prompt template."""

from __future__ import annotations

from importlib.resources import files
from string import Template

from lumon.agents.mark.model import Message, WorkspaceContext
from lumon.errors import AgentConfigError
from lumon.flows.model import FlowBrief

_TEMPLATE_PACKAGE = "lumon.agents.mark.templates"
_PROMPT_TEMPLATE_NAME = "workspace_prompt.md"


class MarkPromptRenderer:
    """Render one complete Agent prompt from a packaged Markdown template.

    The renderer owns the textual representation of Mark's prompt. Callers
    provide typed Workspace data, conversation history, and the selected SOUL;
    they do not need to know the template syntax or resource location.
    """

    def __init__(self, template_text: str | None = None) -> None:
        """Create a renderer using the packaged template or supplied text."""

        source = template_text if template_text is not None else _load_template()
        if not source.strip():
            raise AgentConfigError("Packaged Mark Workspace prompt is empty.")
        self._template = Template(source)

    def render(
        self,
        *,
        context: WorkspaceContext,
        history: tuple[Message, ...],
        soul: str,
        user_message: str,
    ) -> str:
        """Render a self-contained prompt for one Workspace request."""

        repository_text = (
            "\n".join(f"- {repository}" for repository in context.repositories)
            or "(none registered)"
        )
        flow_text = _render_flow_briefs(context.flow_briefs)
        return self._template.substitute(
            soul=soul,
            workspace_name=context.name,
            workspace_id=context.workspace_id,
            workspace_root=context.path,
            agents_path=context.agents_path,
            manifest_path=context.manifest_path,
            workspace_config_path=context.workspace_config_path,
            repository_text=repository_text,
            flow_briefs=flow_text,
            agents_text=context.agents_text,
            history_text=_render_history(history),
            user_message=user_message,
        )

    def render_resume(self, *, flow_briefs: tuple[FlowBrief, ...], user_message: str) -> str:
        """Render fresh flow routing context for a resumed Codex session."""

        return (
            "<lumon-flow-context>\n"
            "The following enabled Workspace flow IDs and briefs are current for this turn.\n"
            f"{_render_flow_briefs(flow_briefs)}\n"
            "Decide which flow applies, then read its full Markdown file before following it.\n"
            "If the request is ambiguous, ask the user to choose a flow.\n"
            "</lumon-flow-context>\n\n"
            f"<user-message>\n{user_message}\n</user-message>"
        )


def _load_template() -> str:
    try:
        return files(_TEMPLATE_PACKAGE).joinpath(_PROMPT_TEMPLATE_NAME).read_text(encoding="utf-8")
    except (ModuleNotFoundError, OSError, UnicodeDecodeError) as exc:
        raise AgentConfigError("Packaged Mark Workspace prompt is unavailable.") from exc


def _render_history(history: tuple[Message, ...]) -> str:
    if not history:
        return "(no previous messages)"
    lines: list[str] = []
    for item in history:
        speaker = "user" if item.direction == "inbound" else "mark"
        lines.append(f"[{speaker}] {item.text}")
    return "\n".join(lines)


def _render_flow_briefs(flow_briefs: tuple[FlowBrief, ...]) -> str:
    if not flow_briefs:
        return "(no enabled Workspace flows)"
    lines: list[str] = []
    for flow in flow_briefs:
        lines.append(f"- id: {flow.flow_id}; brief: {flow.brief}; full detail: {flow.path}")
    return "\n".join(lines)
