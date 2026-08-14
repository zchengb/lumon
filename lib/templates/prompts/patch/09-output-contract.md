# Patch Result

Write `<workspace-root>/lumen/results/patch-result.json` with this shape:

```json
{
  "schema_version": "1.0",
  "patch_status": "completed",
  "jira_key": "PROJ-123",
  "summary": "Short honest summary",
  "repository_decision": {"repositories": ["service"], "reason": "Evidence"},
  "repos_touched": [{"name": "service", "files_changed": ["src/example.ts"], "commit_subject": "[lumon] #PROJ-123 fix: correct behavior"}],
  "self_checks": [{"label": "git diff check", "status": "passed", "summary": "No whitespace errors"}],
  "question": "",
  "failures": []
}
```

For a multi-repository patch, include one `repos_touched` entry per changed repository and report the exact files and commit subject for each one.

Allowed `patch_status` values are `completed`, `blocked`, `skipped`, and `failed`. Never invent commit SHAs, PR URLs, Jira status, notification status, or test results.
