import { Check, FileText, LoaderCircle, Play, ScanSearch, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ApiError, dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { ScanRun, SettingsUpdate, WorkspaceSettings } from "../../shared/types";

interface AutoScanPageProps {
  workspaceId: string;
  settings: WorkspaceSettings;
  onSave: (update: SettingsUpdate) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
  onError: (message: string | null) => void;
}

export function AutoScanPage({
  workspaceId,
  settings,
  onSave,
  onDirtyChange,
  onError,
}: AutoScanPageProps): React.JSX.Element {
  const { formatDate, t } = useI18n();
  const [enabled, setEnabled] = useState(settings.auto_scan.enabled);
  const [lookbackDays, setLookbackDays] = useState(String(settings.auto_scan.lookback_days));
  const [scheduleExpression, setScheduleExpression] = useState(settings.auto_scan.schedule_expression);
  const [hooks, setHooks] = useState(settings.auto_scan.trigger_hooks.join("\n"));
  const [description, setDescription] = useState(settings.auto_scan.workflow_description);
  const [runs, setRuns] = useState<ScanRun[]>([]);
  const [saving, setSaving] = useState(false);
  const [starting, setStarting] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPage, setHistoryPage] = useState(0);
  const pageSize = 10;

  const defaults = useMemo(() => settings.auto_scan, [settings.auto_scan]);
  useEffect(() => {
    setEnabled(defaults.enabled);
    setLookbackDays(String(defaults.lookback_days));
    setScheduleExpression(defaults.schedule_expression);
    setHooks(defaults.trigger_hooks.join("\n"));
    setDescription(defaults.workflow_description);
    onDirtyChange(false);
  }, [defaults, onDirtyChange]);

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

  const hasChanges = enabled !== defaults.enabled
    || lookbackDays !== String(defaults.lookback_days)
    || scheduleExpression !== defaults.schedule_expression
    || hooks !== defaults.trigger_hooks.join("\n")
    || description !== defaults.workflow_description;
  const pageCount = Math.ceil(runs.length / pageSize);
  const visibleRuns = runs.slice(historyPage * pageSize, (historyPage + 1) * pageSize);

  function markDirty(): void {
    onDirtyChange(true);
  }

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const saved = await onSave({
        feishu_webhook: { enabled: settings.feishu_webhook.enabled },
        auto_scan: {
          enabled,
          lookback_days: Number(lookbackDays),
          trigger_hooks: hooks.split(/\r?\n/).map((value) => value.trim()).filter(Boolean),
          schedule_expression: scheduleExpression.trim(),
          workflow_description: description.trim(),
        },
      });
      if (saved) onDirtyChange(false);
    } finally {
      setSaving(false);
    }
  }

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
        {hasChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
      </div>

      <section className="panel settings-panel">
        <div className="panel-heading">
          <div className="settings-title">
            <span className="settings-icon"><ScanSearch size={18} /></span>
            <div><p className="eyebrow">{t("settings.automation")}</p><h2>{t("settings.autoScan")}</h2></div>
          </div>
          <div className="settings-heading-actions">
            <span className={enabled ? "status-pill status-ready" : "status-pill status-neutral"}>
              {enabled && <Check size={13} />}{enabled ? t("settings.enabled") : t("settings.disabled")}
            </span>
            <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
              <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
              <input type="checkbox" role="switch" checked={enabled} aria-label={t("settings.autoScanToggleAria")} onChange={(event) => { setEnabled(event.target.checked); markDirty(); }} />
              <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
            </label>
          </div>
        </div>
        <p className="settings-description">{t("settings.autoScanDescription")}</p>
        <div className="auto-scan-fields">
          <div className="form-grid">
            <div>
              <label className="field-label" htmlFor="auto-scan-lookback">{t("settings.autoScanLookback")}</label>
              <input id="auto-scan-lookback" className="text-input" type="number" min="1" max="365" value={lookbackDays} onChange={(event) => { setLookbackDays(event.target.value); markDirty(); }} />
              <p className="field-help">{t("settings.autoScanLookbackHelp")}</p>
            </div>
            <div>
              <label className="field-label" htmlFor="auto-scan-schedule">{t("settings.autoScanSchedule")}</label>
              <input id="auto-scan-schedule" className="text-input mono" value={scheduleExpression} placeholder="0 12 * * 1-5" onChange={(event) => { setScheduleExpression(event.target.value); markDirty(); }} />
              <p className="field-help">{t("settings.autoScanScheduleHelp")}</p>
            </div>
            <div className="field-full">
              <label className="field-label" htmlFor="auto-scan-hooks">{t("settings.autoScanHooks")}</label>
              <textarea id="auto-scan-hooks" className="text-input text-area mono" rows={3} value={hooks} placeholder="twg.create_bug" onChange={(event) => { setHooks(event.target.value); markDirty(); }} />
              <p className="field-help">{t("settings.autoScanHooksHelp")}</p>
            </div>
            <div className="field-full">
              <label className="field-label" htmlFor="auto-scan-description">{t("settings.autoScanDescriptionLabel")}</label>
              <textarea id="auto-scan-description" className="text-input text-area" rows={5} value={description} onChange={(event) => { setDescription(event.target.value); markDirty(); }} />
              <p className="field-help">{t("settings.autoScanDescriptionHelp")}</p>
            </div>
          </div>
        </div>
        <div className="settings-actions">
          <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || !hasChanges}>
            {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}{t("settings.save")}
          </button>
        </div>
      </section>

      <section className="panel scan-history-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">{t("autoScan.historyEyebrow")}</p><h2>{t("autoScan.historyTitle")}</h2></div>
          <button className="button button-secondary" type="button" onClick={() => void startScan()} disabled={starting}>
            {starting ? <LoaderCircle size={15} className="spin" /> : <Play size={15} />}{t("autoScan.start")}
          </button>
        </div>
        <p className="settings-description">{t("autoScan.historyDescription")}</p>
        {historyLoading ? <div className="loading-inline"><LoaderCircle size={18} className="spin" />{t("autoScan.loadingHistory")}</div> : (
          <div className="table-scroll scan-history-scroll">
            <table className="scan-history-table">
              <thead><tr><th>{t("autoScan.started")}</th><th>{t("autoScan.status")}</th><th>{t("autoScan.findings")}</th><th>{t("autoScan.duration")}</th><th>{t("autoScan.artifacts")}</th></tr></thead>
              <tbody>
                {runs.length ? visibleRuns.map((run) => <tr key={run.run_id}>
                  <td><span className="mono">{formatDate(run.started_at)}</span></td>
                  <td><span className={`status-pill ${run.state === "completed" ? "status-ready" : run.state === "failed" ? "status-danger" : "status-warning"}`}>{run.state}</span></td>
                  <td>{run.findings.length}</td>
                  <td>{run.duration_seconds === null ? "—" : `${run.duration_seconds}s`}</td>
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
