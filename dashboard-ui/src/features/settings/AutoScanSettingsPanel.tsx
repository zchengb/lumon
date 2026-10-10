import { LoaderCircle, Save, ScanSearch } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "../../shared/i18n";
import type { SettingsUpdate, WorkspaceSettings } from "../../shared/types";
import { FieldLabelWithHelp, HelpTooltip } from "../shared/HelpTooltip";

export function AutoScanSettingsPanel({ settings, onSave, onDirtyChange }: {
  settings: WorkspaceSettings;
  onSave: (update: SettingsUpdate) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
}): React.JSX.Element {
  const { t } = useI18n();
  const saved = settings.auto_scan;
  const savedHooks = saved.trigger_hooks.join("\n");
  const [enabled, setEnabled] = useState(saved.enabled);
  const [lookbackDays, setLookbackDays] = useState(String(saved.lookback_days));
  const [scheduleExpression, setScheduleExpression] = useState(saved.schedule_expression);
  const [hooks, setHooks] = useState(savedHooks);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEnabled(saved.enabled);
    setLookbackDays(String(saved.lookback_days));
    setScheduleExpression(saved.schedule_expression);
    setHooks(savedHooks);
  }, [settings.workspace_id, saved.enabled, saved.lookback_days, saved.schedule_expression, savedHooks]);

  const hasChanges = enabled !== saved.enabled
    || lookbackDays !== String(saved.lookback_days)
    || scheduleExpression !== saved.schedule_expression
    || hooks !== savedHooks;
  useEffect(() => { onDirtyChange(hasChanges); }, [hasChanges, onDirtyChange]);

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const success = await onSave({
        feishu_webhook: { enabled: settings.feishu_webhook.enabled },
        auto_scan: {
          enabled,
          lookback_days: Number(lookbackDays),
          trigger_hooks: hooks.trim() ? [hooks.trim()] : [],
          schedule_expression: scheduleExpression.trim(),
        },
      });
      if (success) onDirtyChange(false);
    } finally {
      setSaving(false);
    }
  }

  return <section className="panel settings-panel auto-scan-settings-panel">
    <div className="panel-heading">
      <div className="settings-title">
        <span className="workspace-glyph glyph-amber"><ScanSearch size={18} /></span>
        <div>
          <p className="eyebrow">{t("settings.automation")}</p>
          <div className="field-label-heading">
            <h2>{t("settings.autoScan")}</h2>
            <HelpTooltip helpId="auto-scan-overview-help" label={t("settings.autoScan")} help={t("settings.autoScanDescription")} />
          </div>
        </div>
      </div>
      <div className="settings-heading-actions">
        {hasChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
        <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
          <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
          <input type="checkbox" role="switch" checked={enabled} aria-label={t("settings.autoScanToggleAria")} onChange={(event) => setEnabled(event.target.checked)} />
          <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
        </label>
      </div>
    </div>
    <div className="auto-scan-fields">
      <div className="form-grid">
        <div>
          <FieldLabelWithHelp htmlFor="auto-scan-lookback" helpId="auto-scan-lookback-help" label={t("settings.autoScanLookback")} help={t("settings.autoScanLookbackHelp")} />
          <input id="auto-scan-lookback" className="text-input" type="number" min="1" max="365" value={lookbackDays} aria-describedby="auto-scan-lookback-help" onChange={(event) => setLookbackDays(event.target.value)} />
        </div>
        <div>
          <FieldLabelWithHelp htmlFor="auto-scan-schedule" helpId="auto-scan-schedule-help" label={t("settings.autoScanSchedule")} help={t("settings.autoScanScheduleHelp")} />
          <input id="auto-scan-schedule" className="text-input mono" value={scheduleExpression} placeholder="0 12 * * 1-5" aria-describedby="auto-scan-schedule-help" onChange={(event) => setScheduleExpression(event.target.value)} />
        </div>
        <div className="field-full">
          <label className="field-label" htmlFor="auto-scan-hooks">{t("settings.autoScanHooks")}</label>
          <textarea id="auto-scan-hooks" className="text-input text-area" rows={6} maxLength={8000} value={hooks} placeholder={t("settings.autoScanHooksPlaceholder")} onChange={(event) => setHooks(event.target.value)} />
        </div>
      </div>
    </div>
    <div className="settings-actions">
      <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || !hasChanges} aria-label={`${t("settings.webhookSave")} ${t("settings.autoScan")}`}>
        {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}{t("settings.webhookSave")}
      </button>
    </div>
  </section>;
}
