## Findings And Auto-Fix

Report only findings with code evidence, a realistic trigger, and concrete impact. Each finding needs:

- short `title` and `severity`;
- `repository`, `file`, exact `line_range`, and redacted `code_snippet`;
- `impact`, `trigger`, `root_cause`, and `suggestion`;
- `validation: "Skipped: lightweight review-only mode"`;
- `pr_url: null` unless post-scan has created the real PR.

Avoid vague claims such as “might be risky”, “could be refactored”, or “potential bug” without evidence.

Create a local auto-fix commit only when the finding is confirmed High, the trigger is realistic, the fix is minimal and low risk, the worktree was clean, and that repository allows auto-fix/PR creation. Add focused tests when practical, but do not run project validation in review-only mode.

For each qualifying fix: create the auto-fix branch, edit only the affected behavior, inspect Git identity/history, commit with the Lumon format, record `auto_fix`, and leave pushing/PR creation to post-scan. If any step fails, record `auto_fix.status: failed` and the exact error.
