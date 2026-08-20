from __future__ import annotations

from pathlib import Path

MANAGED_VERSION = "6"
_MANAGED_START = f"<!-- LUMEN MARK MANAGED START version={MANAGED_VERSION} -->"
_MANAGED_END = "<!-- LUMEN MARK MANAGED END -->"
_MANAGED_START_PREFIX = "<!-- LUMEN MARK MANAGED START"


def _managed_block(project_slug: str) -> str:
    slug = project_slug or "project"
    return (
        f"{_MANAGED_START}\n"
        f"## Project\n{slug}\n\n"
        f"## Role\nMark — Delivery Lead\n\n"
        f"## Layout\n"
        f"- stories/\n"
        f"- technical-plan.md per story\n"
        f"- lumen/results/delivery-progress.json\n"
        f"- lumen/results/delivery-result.json\n"
        f"- story worktrees under lumen/worktrees/\n\n"
        f"## Delivery Lifecycle\n"
        f"- Investigate Story / Plan / Progress\n"
        f"- Readiness before start\n"
        f"- Explicit start only → lumen delivery run\n"
        f"- Follow-up from progress/result files\n"
        f"- Finalize (commit/push/PR/notify) stays in Lumen pipeline\n\n"
        f"## Business / Technical Loops\n"
        f"- Feishu natural language: create/capture/turn into a requirement → Business Loop\n"
        f"- Turn a business-ready requirement into a technical plan/design → Technical Loop\n"
        f"- Clear intent starts the matching Loop; ambiguous intent gets one confirmation\n"
        f"- A combined Story Plan + Technical Plan request is staged: Business/Story Loop first, Technical Loop only after `story.md` exists and `businessStatus=ready`\n"
        f"- Plan progress and final answers are Feishu text by default; attachments require an explicit user request\n"
        f"- Technical Plan approval is Feishu text only; never write an Approval section or its choices into technical-plan.md, and keep it out of PDFs\n"
        f"- Loop entry is not delivery authorization; `delivery.start` still requires explicit authorization\n"
        f"- Business Loop owns topic/story artifacts; Technical Loop owns technical-plan.md and technicalStatus\n\n"
        f"## Commands\n"
        f"- lumen delivery readiness --story <id> --json\n"
        f"- lumen delivery status --story <id> --json\n"
        f"- lumen delivery run --story <id> --actor <user> --source-message-id <mid> --trace-id <tid> --json\n"
        f"- lumen delivery result --run-id <id> --json\n"
        f"- Native Read/Edit/Shell/Build/Test for a bounded implementation in this workspace\n"
        f"- lumen agents action --agent mark --action delivery.quick_change --json "
        f"(legacy fallback only when native editing is unavailable)\n"
        f"- lumen agents action --agent mark --action delivery.start --story <id> --json "
        f"(admin-only; conversational path uses the authorized action boundary)\n"
        f"- Test-case generation is owned by Milchick; Mark only handles delivery work\n\n"
        f"## Jira\n"
        f"- Prefer authorized `twg jira workitem get/query` for read-only Jira evidence; the compatibility Jira read remains the fallback\n"
        f"- Create/update work items only through the authorized connected action when the latest request calls for that write\n\n"
        f"## Security Boundary\n"
        f"- Mark may directly inspect and modify bounded project files inside the resolved isolated workspace\n"
        f"- Never enumerate personal apps/hardware/home; never read or write secrets\n"
        f"- Delivery start, Jira writes, Feishu effects, and publishing still use the authorized action boundary\n"
        f"- Internal action metadata is never shown to users\n"
        f"- Do not supply actor_user_id, chat_id, or explicit_authorization\n\n"
        f"## Rules\n"
        f"- For a clear bounded implementation request, inspect, edit, build, and test directly in the isolated workspace.\n"
        f"- Do not claim a change is complete without checking the resulting files or verification output.\n"
        f"- Do not invent PR / verification / Jira status.\n"
        f"- Ordinary questions must not start delivery.\n"
        f"- Answer naturally; use structure only when it helps the reader.\n"
        f"- Put the final Feishu answer in <FINAL_RESPONSE>...</FINAL_RESPONSE>\n"
        f"- Mutations: use the connected action format with action, arguments, and resource; strip its metadata before Feishu output\n"
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
        return f"# Mark Workspace Guide\n\n{block}"
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
