import { FileText, LoaderCircle, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { ScanRun } from "../../shared/types";

interface AutoScanPageProps {
  workspaceId: string;
  onError: (message: string | null) => void;
}

export function AutoScanPage({
  workspaceId,
  onError,
}: AutoScanPageProps): React.JSX.Element {
  const { formatDate, t } = useI18n();
  const [runs, setRuns] = useState<ScanRun[]>([]);
  const [starting, setStarting] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPage, setHistoryPage] = useState(0);
  const pageSize = 10;

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    dashboardApi.listScans(workspaceId)
      .then((next) => {
        if (!cancelled) {
          setRuns(next);
          setHistoryPage(0);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) onError(reason instanceof ApiError ? reason.message : t("app.dashboardRequestFailed"));
      })
      .finally(() => { if (!cancelled) setHistoryLoading(false); });
    return () => { cancelled = true; };
  }, [onError, t, workspaceId]);

  const pageCount = Math.ceil(runs.length / pageSize);
  const visibleRuns = runs.slice(historyPage * pageSize, (historyPage + 1) * pageSize);
  const stateLabels: Record<string, string> = {
    running: t("autoScan.running"),
    completed: t("autoScan.completed"),
    completed_with_findings: t("autoScan.completed_with_findings"),
    completed_with_failures: t("autoScan.completed_with_failures"),
    failed: t("autoScan.failed"),
  };

  async function startScan(): Promise<void> {
    if (!window.confirm(t("autoScan.startConfirm"))) return;
    setStarting(true);
    onError(null);
    try {
      const next = await dashboardApi.startScan(workspaceId);
      setRuns((current) => [next, ...current.filter((run) => run.run_id !== next.run_id)]);
      setHistoryPage(0);
    } catch (reason: unknown) {
      onError(reason instanceof ApiError ? reason.message : t("app.dashboardRequestFailed"));
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("autoScan.eyebrow")}</p>
          <h1>{t("autoScan.title")}</h1>
          <p className="muted">{t("autoScan.subtitle")}</p>
        </div>
      </div>

      <section className="panel scan-history-panel">
        <div className="panel-heading">
          <h2>{t("autoScan.historyTitle")}</h2>
          <button className="button button-secondary" type="button" onClick={() => void startScan()} disabled={starting}>
            {starting ? <LoaderCircle size={15} className="spin" /> : <Play size={15} />}{t("autoScan.start")}
          </button>
        </div>
        {historyLoading ? <div className="loading-inline"><LoaderCircle size={18} className="spin" />{t("autoScan.loadingHistory")}</div> : (
          <div className="table-scroll scan-history-scroll">
            <table className="scan-history-table">
              <thead><tr><th>{t("autoScan.started")}</th><th>{t("autoScan.status")}</th><th>{t("autoScan.findings")}</th><th>{t("autoScan.duration")}</th><th>{t("autoScan.artifacts")}</th></tr></thead>
              <tbody>
                {runs.length ? visibleRuns.map((run) => <tr key={run.run_id}>
                  <td><span className="mono">{formatDate(run.started_at)}</span></td>
                  <td><span className={`status-pill ${run.state === "completed" ? "status-ready" : run.state === "failed" ? "status-danger" : "status-warning"}`} title={run.failures.join("\n") || undefined}>{stateLabels[run.state] ?? run.state}</span></td>
                  <td><SeverityBreakdown findings={run.findings} /></td>
                  <td>{run.duration_seconds === null ? "—" : `${Math.floor(run.duration_seconds / 60)}m${run.duration_seconds % 60}s`}</td>
                  <td className="scan-artifacts">
                    {run.html_available && <a href={`/api/workspaces/${workspaceId}/scans/${encodeURIComponent(run.run_id)}/artifacts/html`} target="_blank" rel="noreferrer"><FileText size={14} />HTML</a>}
                    {run.pdf_available && <a href={`/api/workspaces/${workspaceId}/scans/${encodeURIComponent(run.run_id)}/artifacts/pdf`} target="_blank" rel="noreferrer"><FileText size={14} />PDF</a>}
                    {!run.html_available && !run.pdf_available && "—"}
                  </td>
                </tr>) : <tr><td colSpan={5} className="empty-table">{t("autoScan.noHistory")}</td></tr>}
              </tbody>
            </table>
          </div>
        )}
        {pageCount > 1 && <div className="scan-history-pagination">
          <button className="button button-secondary" type="button" disabled={historyPage === 0} onClick={() => setHistoryPage((page) => page - 1)}>{t("autoScan.previous")}</button>
          <span className="muted">{t("autoScan.pageOf", { current: historyPage + 1, total: pageCount })}</span>
          <button className="button button-secondary" type="button" disabled={historyPage >= pageCount - 1} onClick={() => setHistoryPage((page) => page + 1)}>{t("autoScan.next")}</button>
        </div>}
      </section>
    </div>
  );
}

function SeverityBreakdown({ findings }: { findings: ScanRun["findings"] }): React.JSX.Element {
  const { t } = useI18n();
  const levels = [
    ["High", t("autoScan.high"), "high"],
    ["Medium", t("autoScan.medium"), "medium"],
    ["Low", t("autoScan.low"), "low"],
  ] as const;
  const present = levels.map(([severity, label, tone]) => ({
    label,
    tone,
    count: findings.filter((finding) => finding.severity === severity).length,
  })).filter(({ count }) => count > 0);

  return present.length ? <span className="scan-severity-breakdown">
    {present.map(({ label, tone, count }) => <span className={`scan-severity scan-severity-${tone}`} key={tone}>{label}: {count}</span>)}
  </span> : <>—</>;
}
