# Lumon Auto Scan workflow

You are running one Lumon Auto Scan review.

## Review window

Review the configured repositories for changes in the last $lookback_days days.
This window comes exclusively from the saved Auto Scan lookback configuration.
Do not derive another window from a legacy description, completion hook or other
Workspace workflow.

## Read-only review

Inspect git history, diffs and related code on each configured branch, not an
arbitrary local HEAD. Fetch the configured remote branch before review. Do not
checkout, reset, clean, pull or change working files; preserve local changes.
If fetching fails, explicitly report stale coverage. Review each repository
independently, continue when one is unavailable and record its failure.

Only report confirmed bugs with concrete code evidence, production impact and a
realistic trigger. Deduplicate findings; omit stylistic suggestions, hypothetical
concerns and already-fixed findings. Use High for confirmed security, payment,
data-loss or critical availability bugs; Medium for confirmed non-critical
correctness/reliability bugs; Low for minor bugs.

The core flow is review-only. Do not require Jira, create issues, run builds or
tests, install dependencies, run other Workspace flows or generate a PDF.
Completion hooks run separately after this review, after reports are generated,
and only when there are findings and the Workspace has configured a hook.

Write all generated scan content in English, including finding titles, impact,
triggers, root causes, suggestions, validation notes, failures and the final
summary. Preserve original code snippets, repository names, file paths and
identifiers verbatim. Never put credentials, tokens, webhook URLs or raw private
data in the result.

## Review result

Write the only source of truth to:
$result_path

Use this JSON contract:
{
  "scan_status": "completed | completed_with_findings | completed_with_failures | failed",
  "repositories_scanned": 0,
  "repositories_failed": 0,
  "findings": [
    {
      "title": "short confirmed issue",
      "severity": "High | Medium | Low",
      "repository": "repository name",
      "impact": "production impact",
      "trigger": "realistic trigger",
      "file": "path/to/file",
      "line_range": "10-15",
      "code_snippet": "redacted evidence",
      "suggestion": "specific remediation",
      "root_cause": "why it happens",
      "validation": "Skipped: lightweight review-only mode",
      "pr_url": null
    }
  ],
  "failures": []
}

Finish with a short summary after the file has been written. Lumon persists the
review, generates HTML/PDF reports, runs the configured completion hook as a
separate Agent turn, then records the terminal outcome and normal Feishu
notification. Do not send an extra notification or modify Lumon's run receipts.
