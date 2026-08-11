from __future__ import annotations

from pathlib import Path

MANAGED_VERSION = "5"
_MANAGED_START = f"<!-- LUMEN MILCHICK MANAGED START version={MANAGED_VERSION} -->"
_MANAGED_END = "<!-- LUMEN MILCHICK MANAGED END -->"
_MANAGED_START_PREFIX = "<!-- LUMEN MILCHICK MANAGED START"


def _managed_block(project_slug: str) -> str:
    slug = project_slug or "project"
    return (
        f"{_MANAGED_START}\n"
        f"## Project\n{slug}\n\n"
        f"## Role\nMilchick — Engineering Operations Manager\n\n"
        f"## Direct capabilities\n"
        f"- agent.list / agent.health\n"
        f"- agent.job.create / list / show / cancel / retry\n"
        f"- jira.workitem.get / jira.workitem.query / jira.sprint.untested.report (via host TWG)\n"
        f"- jira.workitem.create / jira.workitem.update (via host TWG; Agent-selected structured action)\n"
        f"- project.status / workflow.status / schedule.status\n\n"
        f"## Test-case execution\n"
        f"- Milchick owns test_case.generate after a Jira query/report returns matching work items\n"
        f"- Never ask redundant confirmation before delegation\n"
        f"- Child jobs may set depends_on\n\n"
        f"## Natural-language routing\n"
        f"- A readable screenshot or bounded wording request is not a Jira request by default\n"
        f"- Route clear source or delivery work to Mark without pre-reading the repository or inferring files\n"
        f"- The host preserves the original message and image context; Mark reads the workspace himself\n"
        f"- Ask only when the owner, capability, user intent, or outcome is genuinely unclear\n\n"
        f"## Security Boundary\n"
        f"- Workspace-isolated; no host enumeration\n"
        f"- Jira create/update only via <ACTION_REQUEST>; no shell twg\n"
        f"- No risk.resolve; test_case.generate may write only the configured test-case destination\n"
        f"- Mutations use an internal <ACTION_REQUEST> channel; never ask the user to write or confirm it\n\n"
        f"## Rules\n"
        f"- Put Feishu answers in <FINAL_RESPONSE>...</FINAL_RESPONSE>\n"
        f"- Summarize parent-job graphs when asked for status\n"
        f"{_MANAGED_END}\n"
    )


def _upsert_managed_block(existing: str, project_slug: str) -> str:
    block = _managed_block(project_slug)
    text = existing or ""
    start = text.find(_MANAGED_START_PREFIX)
    if start >= 0:
        end = text.find(_MANAGED_END, start)
        if end >= 0:
            end += len(_MANAGED_END)
            return text[:start].rstrip() + "\n\n" + block + text[end:].lstrip("\n")
    if not text.strip():
        return f"# Milchick Workspace Guide\n\n{block}"
    return text.rstrip() + "\n\n" + block


def ensure_workspace_contract(*, workspace: Path, project_slug: str) -> Path:
    from agents.dylan.permission_policy import write_permission_profile

    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    agents = root / "AGENTS.md"
    current = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    updated = _upsert_managed_block(current, project_slug)
    if updated != current:
        agents.write_text(updated, encoding="utf-8")
    write_permission_profile(root, force=True)
    return root
