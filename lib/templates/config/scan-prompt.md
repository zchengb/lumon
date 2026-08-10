# Lumen Scan Prompt Index

This workspace uses **modular prompt snippets** under `prompts/scan/`.

At scan time, `run-scan.sh` composes a short agent prompt from `prompts/scan/manifest.json`:

1. Generated runtime scan context
2. Inline core snippet(s) listed under `inline`
3. A `# Scan Prompt Catalog` table for the remaining snippets

The agent reads catalog files from disk when needed. Snippets marked `REQUIRED` must be read before classifying findings or writing `scan-result.json`.

Legacy manifests that only list `snippets` still inline every file (old behavior).

## Snippet modules

| File | Purpose | Default load |
|------|---------|--------------|
| `01-role-and-mission.md` | Agent role, wrapper boundaries, review-only mode | Inlined |
| `02-pipeline.md` | End-to-end scan steps | Catalog |
| `03-configuration.md` | Config files and workspace layout | Catalog |
| `04-workspace-and-worktrees.md` | Git worktree isolation rules | Catalog |
| `05-review-only-mode.md` | No build/test command policy | Catalog |
| `06-issue-registry.md` | Cross-run issue tracking | Catalog |
| `07-error-handling.md` | Scan status and failure recording | Catalog |
| `08-github-pr-and-git.md` | PR, branch, commit, pre-push hook rules | Catalog |
| `09-severity-guideline.md` | **Official High / Medium / Low standard** | Catalog (REQUIRED) |
| `10-findings-and-auto-fix.md` | Finding fields and PR eligibility | Catalog (REQUIRED) |
| `11-output-contract.md` | `scan-result.json` schema | Catalog (REQUIRED) |
| `12-secrets-and-safety.md` | Secret redaction and safety rules | Catalog |
| `13-console-summary.md` | Final stdout summary format | Catalog |

## Customize

- Edit one snippet to change one concern (for example severity rules in `09-severity-guideline.md`).
- Change `inline` / `catalog` entries in `manifest.json` to control what is inlined vs listed.
- Run `lumen upgrade --project <slug>` to refresh bundled snippets from the CLI release (your edits are backed up under `config/.template-backups/`).

## Compose manually

```bash
python3 ~/.lumon/lib/scripts/compose_scan_prompt.py /path/to/workspace/lumen
```
