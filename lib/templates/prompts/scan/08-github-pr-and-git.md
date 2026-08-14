## Git And PR Boundaries

During the scan, do not push branches, run `gh`, or create PRs. After the Agent exits, the wrapper pushes qualifying auto-fix branches and creates PRs with the configured GitHub credentials.

For an approved High auto-fix:

- use `auto-fix/<repo-name>/<short-finding-slug>`;
- commit only in that branch, never the default branch;
- inspect `git config --get user.name`, `user.email`, and recent commit subjects first;
- use `[lumon] #{JIRA_NUMBER} {chore|docs|feat|fix|refactor|style|test}: {message}`;
- leave `pr_url` empty; post-scan fills it only after a real PR exists.

The generated PR title is `[Bug Fix] <Short Description>` and its body contains Bug & Impact, Trigger Scenario, Root Cause, Fix, and Validation. Do not claim a PR, push, SHA, or validation result that has not happened.
