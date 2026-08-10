---
name: lumen-jira-story-import
description: Use when explicitly asked to import an existing Jira Story in a Lumen workspace, or as the required Jira preflight for a Business or Technical Loop. Import the Jira snapshot, then continue into the Business Loop for the same Story. Do not overwrite local Story edits or application source code.
---

<!-- Lumen managed: agent-skill -->

# Lumen Jira Story Import

Prefer the CLI when available:

```bash
lumen jira import <JIRA-KEY> [--project <slug>]
```

Or run the installed helper directly against the workspace root that contains `stories/` and `lumen/`:

```bash
python3 "${LUMEN_HOME:-$HOME/.lumon}/lib/scripts/import_jira_story.py" "<workspace-root>" <JIRA-KEY>
```

The command creates the linked Story folder on first use. On later use it reads Jira again and updates the auditable snapshot without overwriting `story.md`.

When `metadata.json.jiraSyncStatus` is `changed`, compare the newest Jira snapshot with `story.md`, include the reconciliation choices in the first Business Loop question batch, then update the Story only after confirmation. After reconciling, set `jiraSnapshotHash` to `jiraLatestSnapshotHash` and `jiraSyncStatus` to `synced`. Do not overwrite the local Story or start a Technical Loop implicitly.

After a successful import, immediately continue with `$lumen-business-loop` for the imported Story. Do not stop at an offer. Summarize missing business decisions, ask the full high-impact clarification checklist in one turn, and drive the Story toward `businessStatus: ready`. Do not update Jira from this skill and do not modify application source code.
