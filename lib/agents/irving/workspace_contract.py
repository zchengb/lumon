from __future__ import annotations

from pathlib import Path

MANAGED_VERSION = "3"
_MANAGED_START = f"<!-- LUMEN IRVING MANAGED START version={MANAGED_VERSION} -->"
_MANAGED_END = "<!-- LUMEN IRVING MANAGED END -->"
_MANAGED_START_PREFIX = "<!-- LUMEN IRVING MANAGED START"


def _managed_block(project_slug: str) -> str:
    slug = project_slug or "project"
    return (
        f"{_MANAGED_START}\n"
        f"## Project\n{slug}\n\n"
        f"## Role\nIrving — Remediation Engineer\n\n"
        f"## Direct capabilities\n"
        f"- risk.read\n"
        f"- risk.mark_remediated (explicit authorization only)\n\n"
        f"## Engineering work\n"
        f"- Inspect, edit, build, and test bounded remediation changes directly in this isolated workspace\n"
        f"- Use the legacy delivery broker only when a native workspace tool is unavailable\n\n"
        f"## Jira\n"
        f"- Prefer authorized `twg jira workitem get/query` for read-only Jira evidence; the compatibility Jira read remains the fallback\n"
        f"- Create/update work items only through a connected action when the latest request calls for that write\n\n"
        f"## Security Boundary\n"
        f"- Workspace-isolated; no personal-machine enumeration or secret access\n"
        f"- Code changes and local verification may be direct; Jira, remediation state, Feishu effects, and publishing use connected actions\n\n"
        f"## Rules\n"
        f"- Put the final Feishu answer in <FINAL_RESPONSE>...</FINAL_RESPONSE>\n"
        f"- Prefer careful root-cause investigation over rushed patches\n"
        f"- Report evidence and verification honestly; answer naturally without a forced template\n"
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
        return f"# Irving Workspace Guide\n\n{block}"
    return text.rstrip() + "\n\n" + block


def ensure_workspace_contract(*, workspace: Path, project_slug: str) -> Path:
    from agents.dylan.permission_policy import write_workspace_write_permission_profile

    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    agents = root / "AGENTS.md"
    current = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    updated = _upsert_managed_block(current, project_slug)
    if updated != current:
        agents.write_text(updated, encoding="utf-8")
    write_workspace_write_permission_profile(root, force=True)
    return root
