from __future__ import annotations

from pathlib import Path

from agents.capabilities import AgentCapabilities
from agents.definitions import AgentDefinition
from agents.mark.delivery_adapter import DeliveryActionAdapter
from agents.mark.session_bootstrap import PROTOCOL_VERSION, SOUL_VERSION, build_bootstrap_prompt, build_resume_prompt
from agents.mark.workspace_contract import ensure_workspace_contract
from agents.project_resolver import known_project_slugs, load_chat_project_map, resolve_project
from agents.security.actions import JIRA_ACTIONS, JIRA_MUTATION_ACTIONS, MARK_ACTIONS


def _resolve_workspace(project_slug: str, chat_id: str) -> tuple[str, Path]:
    project = resolve_project(slug=project_slug, chat_id=chat_id, mapping=load_chat_project_map())
    if project is None and not project_slug:
        known = sorted(known_project_slugs())
        if len(known) == 1:
            project = resolve_project(slug=known[0], mapping=load_chat_project_map())
    if project is None or not project.get("workspace"):
        raise RuntimeError("workspace not resolved")
    slug = str(project.get("slug") or project_slug or "").strip()
    workspace = Path(str(project["workspace"])).expanduser().resolve()
    parent = workspace.parent
    if (parent / "stories").is_dir():
        workspace = parent
    elif not (workspace / "stories").is_dir():
        for child in workspace.iterdir() if workspace.is_dir() else []:
            if child.is_dir() and (child / "stories").is_dir():
                workspace = child
                break
    if not workspace.is_dir():
        raise RuntimeError(f"workspace missing: {workspace}")
    return slug, workspace


MARK_DEFINITION = AgentDefinition(
    id="mark",
    display_name="Mark",
    role="delivery",
    soul_path=Path(__file__).with_name("soul.md"),
    soul_version=SOUL_VERSION,
    protocol_version=PROTOCOL_VERSION,
    workflow="auto_delivery",
    result_contract="delivery-result.json",
    permission_profile="delivery_conversational",
    capabilities=AgentCapabilities(
        actions=MARK_ACTIONS,
        read_scopes=("delivery_docs", "story", "technical_plan", "jira"),
        filesystem_mode="workspace_read",
        network_profile="deny",
        secret_profile="isolated",
        direct_workspace_write=False,
        allowed_workflows=(
            "delivery.readiness",
            "delivery.status",
            "delivery.run",
            "delivery.cancel",
            "delivery.quick_change",
            "loop.business",
            "loop.technical",
            *JIRA_ACTIONS,
        ),
        allowed_mutations=("delivery.start", "delivery.quick_change", *JIRA_MUTATION_ACTIONS),
        external_side_effects=("feishu.bitable.write", "jira"),
    ),
    build_bootstrap_prompt=build_bootstrap_prompt,
    build_resume_prompt=build_resume_prompt,
    ensure_workspace_contract=ensure_workspace_contract,
    resolve_workspace=_resolve_workspace,
    action_adapter=DeliveryActionAdapter(),
    config_key="mark",
)
