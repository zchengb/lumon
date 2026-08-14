from __future__ import annotations

from pathlib import Path

MANAGED_VERSION = "5"
_MANAGED_START = f"<!-- LUMEN MANAGED START version={MANAGED_VERSION} -->"
_MANAGED_END = "<!-- LUMEN MANAGED END -->"
_MANAGED_START_PREFIX = "<!-- LUMEN MANAGED START"


def _managed_block(project_slug: str) -> str:
    slug = project_slug or "project"
    return (
        f"{_MANAGED_START}\n"
        f"## Project\n{slug}\n\n"
        f"## Layout\n"
        f"- config/\n"
        f"- results/\n"
        f"- risk/risk.sqlite3\n"
        f"- state/\n"
        f"- logs/\n\n"
        f"## Finding Lifecycle\n"
        f"- Risk Store is the sole lifecycle source of truth\n"
        f"- User primary status: Open / Resolved / Reopened / Ignored\n"
        f"- Progress report: inspect, propose Mark Remediated when useful, no write without confirmation\n"
        f"- Explicit resolve: execute resolve once → Resolved; do not auto-ask Verification\n"
        f"- Resolution basis / verification are detail evidence only\n"
        f"- Prefer Jira keys in user-facing replies\n\n"
        f"## Status Vocabulary\n"
        f"- Open\n"
        f"- Resolved\n"
        f"- Reopened\n"
        f"- Ignored\n\n"
        f"## Resolution Authority\n"
        f"- Owner may explicitly resolve when project policy allows\n"
        f"- High / Reopened / Security may require verification or policy override\n"
        f"- Do not claim verification is runnable when verification-status.available is false\n"
        f"- Policy decisions come from project config, not personal preference\n\n"
        f"## Risk commands\n"
        f"- lumen risk recent --project {slug} --days 7 --json\n"
        f"- lumen risk unresolved --project {slug} --json\n"
        f"- lumen risk top --project {slug} --limit 5 --json\n"
        f"- lumen risk finding show <id> --json\n"
        f"- lumen risk finding links <id> --json\n"
        f"- lumen risk finding verification-status <id> --json\n"
        f"- lumen risk finding mark-remediated <id> --actor <user> --reason <text> "
        f"--source-message-id <mid> --trace-id <tid> --json\n"
        f"- lumen risk finding resolve <id> --basis user_confirmed --actor <user> "
        f"--source-message-id <mid> --trace-id <tid> --json\n"
        f"- lumen risk reconcile --project {slug} [--dry-run|--repair] --json\n"
        f"- lumen risk trend --project {slug} --json\n"
        f"- lumen scan latest --project {slug} --json\n"
        f"- lumen scan schedule show --project {slug} --json\n"
        f"- lumen scan schedule update --project {slug} --cron \"0 12 * * 1-5\" "
        f"--actor <user> --source-message-id <mid> --trace-id <tid> --json\n"
        f"- lumen agents action --agent dylan --action risk.resolve "
        f"--finding <id> --json  (host/admin only; conversational path prefers ACTION_REQUEST)\n\n"
        f"## Jira\n"
        f"- Prefer authorized `twg jira workitem get/query` for read-only Jira evidence; host reads remain the fallback\n"
        f"- Create/update work items only through <ACTION_REQUEST> when the latest request calls for that write\n\n"
        f"## Security Boundary\n"
        f"- Conversational Dylan is workspace-isolated (no host enumeration)\n"
        f"- Never read/edit ~/Desktop, /Applications, ~/Library, ~/.ssh, or ~/.lumon secrets\n"
        f"- Host mutations go through host-side Capability Broker via <ACTION_REQUEST>\n"
        f"- Do not supply actor_user_id, chat_id, or explicit_authorization\n"
        f"- Do not use python/node/curl/ls/find to probe the host\n\n"
        f"## Verification Policy\n"
        f"- Never pass --observed\n"
        f"- Production verification requires a real adapter; dry-run must not change production state\n"
        f"- Check verification-status before offering verification\n\n"
        f"## Final Response Protocol\n"
        f"- Put the user-facing Feishu answer inside <FINAL_RESPONSE>...</FINAL_RESPONSE>\n"
        f"- For mutations, also emit <ACTION_REQUEST>{{JSON}}</ACTION_REQUEST> (action/arguments/resource only)\n"
        f"- Do not include investigation narration outside that envelope\n\n"
        f"## Mutation Confirmation Rule\n"
        f"- Progress reports require confirmation before mark-remediated\n"
        f"- Explicit resolve must not ask twice and must not auto-ask Verification\n"
        f"- Identity and authorization are host-filled; never invent --actor\n\n"
        f"## Engineering rules\n"
        f"- Inspect before answering.\n"
        f"- Do not invent findings, Jira, PRs, or scan status.\n"
        f"- Never expose secret values in the final response.\n"
        f"- For read-only questions, do not modify files.\n"
        f"- Never write outside the Lumen workspace.\n"
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
        return f"# Workspace Guide\n\n{block}"
    return text.rstrip() + "\n\n" + block


def ensure_workspace_contract(*, workspace: Path, project_slug: str) -> Path:
    root = Path(workspace).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    agents = root / "AGENTS.md"
    current = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    updated = _upsert_managed_block(current, project_slug)
    if updated != current:
        agents.write_text(updated, encoding="utf-8")
    from agents.dylan.permission_policy import write_permission_profile

    write_permission_profile(root, force=True)
    return root
