from __future__ import annotations

from pathlib import Path

MANAGED_VERSION = "4"
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
        f"- Loop entry is not delivery authorization; `delivery.start` still requires explicit authorization\n"
        f"- Business Loop owns topic/story artifacts; Technical Loop owns technical-plan.md and technicalStatus\n\n"
        f"## Commands\n"
        f"- lumen delivery readiness --story <id> --json\n"
        f"- lumen delivery status --story <id> --json\n"
        f"- lumen delivery run --story <id> --actor <user> --source-message-id <mid> --trace-id <tid> --json\n"
        f"- lumen delivery result --run-id <id> --json\n"
        f"- lumen agents action --agent mark --action delivery.quick_change --json "
        f"(bounded explicit change; no Story/technical plan required)\n"
        f"- lumen agents action --agent mark --action delivery.start --story <id> --json "
        f"(host/admin only; conversational path uses the internal host execution channel)\n"
        f"- lumen agents action --agent mark --action test_case.generate --story <Jira-key> --json\n\n"
        f"## Jira\n"
        f"- Read/query work items and active-sprint reports through the host TWG adapter\n"
        f"- Create/update work items only through the internal <ACTION_REQUEST> channel when the latest request calls for that write\n\n"
        f"## Security Boundary\n"
        f"- Conversational Mark is workspace-isolated over delivery docs\n"
        f"- Never enumerate host apps/hardware/home; never modify business source or secrets\n"
        f"- Start delivery / quick changes / generate test cases via the host-side broker; the internal <ACTION_REQUEST> envelope is never shown to users\n"
        f"- Do not supply actor_user_id, chat_id, or explicit_authorization\n\n"
        f"## Test Case Skill\n"
        f"- Compatibility action: Mark / test_case.generate (Milchick is the default coordinator)\n"
        f"- Explicit user intent only (Story/Bug)\n"
        f"- Additive Feishu Bitable writes; never overwrite matching titles\n"
        f"- Reply with generation summary, not every row\n\n"
        f"## Rules\n"
        f"- Do not modify business source in conversational Mark session.\n"
        f"- Do not invent PR / verification / Jira status.\n"
        f"- Ordinary questions must not start delivery.\n"
        f"- Put Feishu answers in <FINAL_RESPONSE>...</FINAL_RESPONSE>\n"
        f"- Mutations: internal <ACTION_REQUEST>{{action,arguments,resource}}</ACTION_REQUEST>; strip it before Feishu output\n"
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
