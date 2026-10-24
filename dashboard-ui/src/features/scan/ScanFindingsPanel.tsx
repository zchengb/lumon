import { useState } from "react";
import { ApiError } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { ScanFinding, ScanRun } from "../../shared/types";
import "./ScanFindingsPanel.css";

type IssueFilter = "all" | "open" | "resolved" | "ignored";

export function ScanFindingsPanel({ runs, loading, unavailable, onIgnore }: {
  runs: ScanRun[]; loading: boolean; unavailable: boolean;
  onIgnore?: (runId: string, findingIndex: number) => Promise<void>;
}): React.JSX.Element {
  const { formatDate, t } = useI18n();
  const [filter, setFilter] = useState<IssueFilter>("open");
  const [ignoring, setIgnoring] = useState<string | null>(null);
  const [ignoreError, setIgnoreError] = useState<string | null>(null);
  const latest = new Map<string, { finding: ScanFinding; run: ScanRun; index: number }>();
  for (const run of [...runs].sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at))) {
    for (const [index, finding] of run.findings.entries()) {
      const id = finding.issue_id.trim();
      const key = JSON.stringify([finding.repository, id && id !== "untracked" ? id : [run.run_id, index]]);
      if (!latest.has(key)) latest.set(key, { finding, run, index });
    }
  }
  const issues = [...latest.entries()];
  const matches = (finding: ScanFinding, value: IssueFilter): boolean => value === "all"
    || (value === "open" ? ["open", "in_progress", "pr_open", "reopened"].includes(normalizedStatus(finding.issue_status))
      : normalizedStatus(finding.issue_status) === value);
  const visible = issues.filter(([, { finding }]) => matches(finding, filter));
  const statusLabel = (status: string): string => ({
    open: t("autoScan.open"), in_progress: t("autoScan.inProgress"), pr_open: t("autoScan.prOpen"),
    reopened: t("autoScan.reopened"), resolved: t("autoScan.resolved"), ignored: t("autoScan.ignored"),
  })[normalizedStatus(status)] ?? status;
  const severityLabel = (severity: string): string => ({
    High: t("autoScan.high"), Medium: t("autoScan.medium"), Low: t("autoScan.low"),
  })[severity] ?? severity;

  async function ignore(key: string, runId: string, index: number): Promise<void> {
    if (!onIgnore || ignoring !== null || !window.confirm(t("autoScan.ignoreConfirm"))) return;
    setIgnoring(key);
    setIgnoreError(null);
    try {
      await onIgnore(runId, index);
    } catch (reason: unknown) {
      setIgnoreError(reason instanceof ApiError && reason.status !== 404 ? reason.message : t("autoScan.ignoreFailed"));
    } finally {
      setIgnoring(null);
    }
  }

  return <section className="panel scan-findings-panel" aria-labelledby="scan-findings-title">
    <div className="panel-heading">
      <h2 id="scan-findings-title">{t("autoScan.issuesTitle")}</h2>
      {!loading && !unavailable && <span className="muted">{t("autoScan.issueCount", { count: visible.length, total: issues.length })}</span>}
    </div>
    {loading ? <p className="scan-findings-empty" role="status">{t("autoScan.loadingHistory")}</p>
      : unavailable ? <p className="scan-findings-empty" role="status">{t("autoScan.issuesUnavailable")}</p>
        : <>
          <div className="scan-finding-filters" role="group" aria-label={t("autoScan.filterIssues")}>
            {(["all", "open", "resolved", "ignored"] as const).map((value) => <button type="button" key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>
              {t(`autoScan.${value}`)} <span>{issues.filter(([, { finding }]) => matches(finding, value)).length}</span>
            </button>)}
          </div>
          <div className="scan-finding-list">
            {ignoreError && <p className="scan-findings-empty" role="alert">{ignoreError}</p>}
            {visible.length ? visible.map(([key, { finding, run, index }]) => <article className="scan-finding" key={key}>
              <header>
                <div className="scan-finding-title-line">
                  <h3>{finding.title}</h3>
                  <span className="scan-finding-tags">
                    <span className={`scan-finding-tag scan-severity scan-severity-${finding.severity.toLowerCase()}`}>{severityLabel(finding.severity)}</span>
                    <span className={`scan-finding-tag status-pill ${normalizedStatus(finding.issue_status) === "resolved" ? "status-ready" : "status-neutral"}`}>{statusLabel(finding.issue_status)}</span>
                  </span>
                </div>
                {onIgnore && !["ignored", "resolved"].includes(normalizedStatus(finding.issue_status)) && <button className="button button-secondary scan-finding-ignore" type="button" disabled={ignoring !== null} onClick={() => void ignore(key, run.run_id, index)}>
                  {ignoring === key ? t("autoScan.ignoring") : t("autoScan.ignore")}
                </button>}
              </header>
              <p className="scan-finding-meta"><code>{finding.issue_id}</code><span>{finding.repository}</span><time dateTime={run.started_at}>{formatDate(run.started_at)}</time></p>
              {finding.impact && <p className="scan-finding-impact">{finding.impact}</p>}
              <details>
                <summary>{t("autoScan.viewDetail")}</summary>
                <dl>
                  <dt>{t("autoScan.location")}</dt><dd><code>{[finding.file, finding.line_range].filter(Boolean).join(":") || t("autoScan.notRecorded")}</code></dd>
                  <dt>{t("autoScan.impact")}</dt><dd>{finding.impact || t("autoScan.notRecorded")}</dd>
                  <dt>{t("autoScan.trigger")}</dt><dd>{finding.trigger || t("autoScan.notRecorded")}</dd>
                  <dt>{t("autoScan.rootCause")}</dt><dd>{finding.root_cause || t("autoScan.notRecorded")}</dd>
                  <dt>{t("autoScan.code")}</dt><dd><pre><code>{finding.code_snippet || t("autoScan.notRecorded")}</code></pre></dd>
                  <dt>{t("autoScan.suggestion")}</dt><dd>{finding.suggestion || t("autoScan.notRecorded")}</dd>
                  <dt>{t("autoScan.validation")}</dt><dd>{finding.validation || t("autoScan.notRecorded")}</dd>
                  <dt>{t("autoScan.sourceScan")}</dt><dd><code>{run.run_id}</code></dd>
                </dl>
              </details>
              {safePrUrl(finding.pr_url) && <a className="scan-finding-pr" href={finding.pr_url!} target="_blank" rel="noopener noreferrer">{t("autoScan.pullRequest")}</a>}
            </article>) : <p className="scan-findings-empty">{t("autoScan.noIssues")}</p>}
          </div>
        </>}
  </section>;
}

function normalizedStatus(status: string): string {
  const normalized = status.trim().toLowerCase();
  return normalized === "ignore" ? "ignored" : normalized;
}

function safePrUrl(url: string | null): boolean {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    return ["https:", "http:"].includes(parsed.protocol) && !parsed.username && !parsed.password;
  } catch {
    return false;
  }
}
