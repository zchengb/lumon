import { AlertCircle, Check, Clock3, LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "../../shared/i18n";
import type { ScanRun } from "../../shared/types";

const stages = ["review", "report", "hooks"] as const;

export function ScanProgressPanel({ run, loading, unavailable, onRefresh }: {
  run: ScanRun | null;
  loading: boolean;
  unavailable: boolean;
  onRefresh: () => void;
}): React.JSX.Element {
  const { locale, t } = useI18n();
  const [now, setNow] = useState(Date.now());
  const live = run?.state === "running";
  const stageIndex = run?.phase === "completed" ? stages.length - 1 : stages.findIndex((stage) => stage === run?.phase);
  const successful = run?.state === "completed" || run?.state === "completed_with_findings";

  useEffect(() => {
    if (!live) return;
    function tick(): void {
      if (document.visibilityState === "visible") setNow(Date.now());
    }
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [live, run?.run_id]);

  const labels = {
    review: t("autoScan.stage.review"),
    report: t("autoScan.stage.report"),
    hooks: t("autoScan.stage.hooks"),
  };

  return <section className="panel scan-progress-panel delivery-progress-panel" aria-label={t("autoScan.progress")}>
    <div className="panel-heading">
      <h2>{t("autoScan.progress")}</h2>
      <div className="panel-actions">
        {live && <span className="status-pill status-warning"><Clock3 size={13} aria-hidden="true" />{t("autoDelivery.live")}</span>}
        <button className="button button-secondary" type="button" disabled={loading} onClick={onRefresh}><RefreshCw size={15} aria-hidden="true" />{t("overview.refresh")}</button>
      </div>
    </div>
    {loading ? <div className="loading-inline" role="status"><LoaderCircle size={18} className="spin" />{t("autoScan.loadingHistory")}</div>
      : unavailable ? <p className="delivery-empty" role="status">{t("autoScan.progressUnavailable")}</p>
      : run ? <div className="delivery-progress-body">
        <div className="delivery-facts">
          <div><span>{t("autoScan.status")}</span><ScanStatus run={run} /></div>
          <div><span>{t("autoScan.currentStage")}</span><strong>{successful ? t("autoScan.completed") : labels[stages[stageIndex]] ?? run.phase}</strong></div>
          <div><span>{t("autoScan.started")}</span><strong>{new Date(run.started_at).toLocaleString(locale, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</strong></div>
          <div><span>{t("autoScan.duration")}</span><strong className="scan-progress-duration">{scanDuration(run, now)}</strong></div>
        </div>
        <ol className="delivery-stages scan-stages" aria-label={t("autoScan.stages")}>
          {stages.map((stage, index) => {
            const complete = successful || index < stageIndex;
            const active = index === stageIndex && !successful;
            const running = active && live;
            const failed = active && run.state === "failed";
            return <li key={stage} className={complete ? "is-complete" : active ? `is-active ${running ? "is-running" : ""} ${failed ? "is-failed" : ""}` : ""} aria-current={active ? "step" : undefined}>
              <span className="delivery-stage-marker">{complete ? <Check size={13} aria-hidden="true" /> : running ? <LoaderCircle size={13} className="spin" aria-hidden="true" /> : active && !live ? <AlertCircle size={13} aria-hidden="true" /> : index + 1}</span>
              <span>{labels[stage]}</span>
            </li>;
          })}
        </ol>
      </div> : <p className="delivery-empty">{t("autoScan.noHistory")}</p>}
  </section>;
}

export function ScanStatus({ run }: { run: ScanRun }): React.JSX.Element {
  const { t } = useI18n();
  const tone = run.state === "completed" ? "status-ready" : run.state === "failed" ? "status-danger" : "status-warning";
  const labels: Record<string, string> = {
    running: t("autoScan.running"), completed: t("autoScan.completed"),
    completed_with_findings: t("autoScan.completed_with_findings"),
    completed_with_failures: t("autoScan.completed_with_failures"), failed: t("autoScan.failed"),
  };
  return <span className={`status-pill ${tone}`} title={run.failures.join("\n") || undefined}>{labels[run.state] ?? run.state}</span>;
}

function scanDuration(run: ScanRun, now: number): string {
  const elapsed = Math.floor((now - Date.parse(run.started_at)) / 1000);
  const seconds = run.state === "running" ? Math.max(0, elapsed) : run.duration_seconds;
  return seconds === null || !Number.isFinite(seconds) ? "—" : `${Math.floor(seconds / 60)}m${seconds % 60}s`;
}
