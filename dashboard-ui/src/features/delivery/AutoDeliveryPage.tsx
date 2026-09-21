import { Check, LoaderCircle, Rocket, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "../../shared/i18n";
import type { SettingsUpdate, WorkspaceSettings } from "../../shared/types";

interface AutoDeliveryPageProps {
  settings: WorkspaceSettings;
  onSave: (update: SettingsUpdate) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
}

export function AutoDeliveryPage({
  settings,
  onSave,
  onDirtyChange,
}: AutoDeliveryPageProps): React.JSX.Element {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(settings.auto_delivery.enabled);
  const [triggerHooks, setTriggerHooks] = useState(settings.auto_delivery.trigger_hooks.join("\n"));
  const [scheduleExpression, setScheduleExpression] = useState(
    settings.auto_delivery.schedule_expression,
  );
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEnabled(settings.auto_delivery.enabled);
    setTriggerHooks(settings.auto_delivery.trigger_hooks.join("\n"));
    setScheduleExpression(settings.auto_delivery.schedule_expression);
    onDirtyChange(false);
  }, [
    settings.workspace_id,
    settings.auto_delivery.enabled,
    settings.auto_delivery.trigger_hooks,
    settings.auto_delivery.schedule_expression,
    onDirtyChange,
  ]);

  const hasChanges = enabled !== settings.auto_delivery.enabled
    || triggerHooks !== settings.auto_delivery.trigger_hooks.join("\n")
    || scheduleExpression !== settings.auto_delivery.schedule_expression;

  function markDirty(): void {
    onDirtyChange(true);
  }

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const saved = await onSave({
        feishu_webhook: { enabled: settings.feishu_webhook.enabled },
        auto_delivery: {
          enabled,
          trigger_hooks: triggerHooks.split(/\r?\n/).map((hook) => hook.trim()).filter(Boolean),
          schedule_expression: scheduleExpression.trim(),
        },
      });
      if (saved) onDirtyChange(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("autoDelivery.eyebrow")}</p>
          <h1>{t("autoDelivery.title")}</h1>
          <p className="muted">{t("autoDelivery.subtitle")}</p>
        </div>
        {hasChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
      </div>

      <section className="panel settings-panel">
        <div className="panel-heading">
          <div className="settings-title">
            <span className="settings-icon"><Rocket size={18} /></span>
            <div>
              <p className="eyebrow">{t("settings.automation")}</p>
              <h2>{t("settings.autoDelivery")}</h2>
            </div>
          </div>
          <div className="settings-heading-actions">
            <span className={enabled ? "status-pill status-ready" : "status-pill status-neutral"}>
              {enabled && <Check size={13} />}
              {enabled ? t("settings.enabled") : t("settings.disabled")}
            </span>
            <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
              <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
              <input
                type="checkbox"
                role="switch"
                checked={enabled}
                aria-label={t("settings.autoDeliveryToggleAria")}
                onChange={(event) => { setEnabled(event.target.checked); markDirty(); }}
              />
              <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
            </label>
          </div>
        </div>
        <p className="settings-description">{t("settings.autoDeliveryDescription")}</p>
        <div className="auto-delivery-fields">
          <div className="form-grid">
            <div>
              <label className="field-label" htmlFor="auto-delivery-schedule">
                {t("settings.autoDeliverySchedule")}
              </label>
              <input
                id="auto-delivery-schedule"
                className="text-input mono"
                value={scheduleExpression}
                placeholder="*/5 * * * *"
                onChange={(event) => { setScheduleExpression(event.target.value); markDirty(); }}
              />
              <p className="field-help">{t("settings.autoDeliveryScheduleHelp")}</p>
            </div>
            <div className="field-full">
              <label className="field-label" htmlFor="auto-delivery-hooks">
                {t("settings.autoDeliveryHooks")}
              </label>
              <textarea
                id="auto-delivery-hooks"
                className="text-input text-area mono"
                rows={3}
                value={triggerHooks}
                placeholder="jira.delivery_ready"
                onChange={(event) => { setTriggerHooks(event.target.value); markDirty(); }}
              />
              <p className="field-help">{t("settings.autoDeliveryHooksHelp")}</p>
            </div>
          </div>
        </div>
        <div className="settings-actions">
          <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || !hasChanges}>
            {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}{t("settings.save")}
          </button>
        </div>
      </section>
    </div>
  );
}
