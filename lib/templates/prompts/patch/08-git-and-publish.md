# Git And Publish

Do not run `git commit`, `git push`, `gh pr create`, `gh pr merge`, or any default-branch write. Lumon owns commit subjects, publication mode, retries, and external links after the result is validated.

Provide one concise `commit_subject` for every repository with changes. Before deciding it, inspect `git log --oneline -n 20` and follow the repository's recent wording and verb. The final subject must use Lumon's enforced format:

```text
[lumon] #<JIRA-KEY> <chore|docs|feat|fix|refactor|style|test>: <imperative summary>
```

Do not use `fix(<JIRA-KEY>): ...` or a human author prefix. Lumon normalizes and validates the subject immediately before `git commit`, but the Agent result must still report the intended canonical subject. Leave the worktree changes present for Lumon finalization.
