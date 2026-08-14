# Delivery Result

Write `<workspace-root>/lumen/results/delivery-result.json`, replacing the previous result for this run. During remediation, merge into the existing result and preserve every prior `repos_touched` entry and `commit_subject`.

Use this shape:

```json
{
  "delivery_status": "completed",
  "docs_dir": "/absolute/path/to/docs-repo",
  "workspace_root": "/absolute/path/to/workspace-root",
  "story_id": "MBPAS-123",
  "story_path": "stories/MBPAS-123-example",
  "jira_key": "MBPAS-123",
  "branch": "feature/MBPAS-123-example",
  "repos_touched": [
    {
      "name": "mbpass-business",
      "path": "/absolute/path/to/worktree",
      "branch": "feature/MBPAS-123-example",
      "files_changed": ["src/main/java/..."],
      "commit_subject": "[lumon] #PROJ-123 feat: add survey filter"
    }
  ],
  "commits": [],
  "pr_urls": [],
  "verification_results": [],
  "failures": [],
  "started_at": "2026-07-08T12:00:00Z",
  "finished_at": "2026-07-08T12:30:00Z"
}
```

Allowed `delivery_status`: `completed`, `ready_for_finalize`, `blocked`, or `failed`.

Do not invent PR URLs, commit SHAs, test results, Jira fields, or Feishu fields. Leave `verification_results` empty. Omit `feishu` and `jira`; the wrapper fills external metadata after verification.
