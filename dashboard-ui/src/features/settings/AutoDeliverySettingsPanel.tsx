import { LoaderCircle, Rocket, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { FieldLabelWithHelp } from "../shared/HelpTooltip";
import { useI18n } from "../../shared/i18n";
import type { DeliveryPublishMode, SettingsUpdate, WorkspaceSettings } from "../../shared/types";

interface AutoDeliverySettingsPanelProps {
  settings: WorkspaceSettings;
  onSave: (update: SettingsUpdate) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
}

export function AutoDeliverySettingsPanel({
  settings,
  onSave,
  onDirtyChange,
}: AutoDeliverySettingsPanelProps): React.JSX.Element {
  const { t } = useI18n();
  const savedHooks = settings.auto_delivery.trigger_hooks.join("\n");
  const [enabled, setEnabled] = useState(settings.auto_delivery.enabled);
  const [triggerHooks, setTriggerHooks] = useState(savedHooks);
  const [scheduleExpression, setScheduleExpression] = useState(
    settings.auto_delivery.schedule_expression,
  );
  const [jiraSite, setJiraSite] = useState(settings.auto_delivery.jira_site);
  const [triggerJql, setTriggerJql] = useState(settings.auto_delivery.trigger_jql);
  const [publishMode, setPublishMode] = useState(settings.auto_delivery.publish_mode);
  const [targetBranch, setTargetBranch] = useState(settings.auto_delivery.target_branch);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEnabled(settings.auto_delivery.enabled);
    setTriggerHooks(savedHooks);
    setScheduleExpression(settings.auto_delivery.schedule_expression);
    setJiraSite(settings.auto_delivery.jira_site);
    setTriggerJql(settings.auto_delivery.trigger_jql);
    setPublishMode(settings.auto_delivery.publish_mode);
    setTargetBranch(settings.auto_delivery.target_branch);
  }, [
    settings.workspace_id,
    settings.auto_delivery.enabled,
    savedHooks,
    settings.auto_delivery.schedule_expression,
    settings.auto_delivery.jira_site,
    settings.auto_delivery.trigger_jql,
    settings.auto_delivery.publish_mode,
    settings.auto_delivery.target_branch,
  ]);

  const hasChanges = enabled !== settings.auto_delivery.enabled
    || triggerHooks !== savedHooks
    || scheduleExpression !== settings.auto_delivery.schedule_expression
    || jiraSite !== settings.auto_delivery.jira_site
    || triggerJql !== settings.auto_delivery.trigger_jql
    || publishMode !== settings.auto_delivery.publish_mode
    || targetBranch !== settings.auto_delivery.target_branch;
  const missingTrigger = enabled && (!jiraSite.trim() || !triggerJql.trim() || !triggerHooks.trim());

  useEffect(() => { onDirtyChange(hasChanges); }, [hasChanges, onDirtyChange]);

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const saved = await onSave({
        feishu_webhook: { enabled: settings.feishu_webhook.enabled },
        auto_delivery: {
          enabled,
          trigger_hooks: triggerHooks.trim() ? [triggerHooks.trim()] : [],
          schedule_expression: scheduleExpression.trim(),
          jira_site: jiraSite.trim(),
          trigger_jql: triggerJql.trim(),
          publish_mode: publishMode,
          target_branch: targetBranch.trim(),
        },
      });
      if (saved) onDirtyChange(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel settings-panel auto-delivery-settings-panel">
      <div className="panel-heading">
        <div className="settings-title">
          <span className="workspace-glyph glyph-rose"><Rocket size={18} /></span>
          <div>
            <p className="eyebrow">{t("settings.automation")}</p>
            <h2>{t("settings.autoDelivery")}</h2>
          </div>
        </div>
        <div className="settings-heading-actions">
          {hasChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
          <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
            <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
            <input
              type="checkbox"
              role="switch"
              checked={enabled}
              aria-label={t("settings.autoDeliveryToggleAria")}
              onChange={(event) => setEnabled(event.target.checked)}
            />
            <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
          </label>
        </div>
      </div>
      <div className="auto-delivery-fields">
        <div className="form-grid">
          <div>
            <FieldLabelWithHelp htmlFor="auto-delivery-schedule" helpId="auto-delivery-schedule-help"
              label={t("settings.autoDeliverySchedule")} help={t("settings.autoDeliveryScheduleHelp")} />
            <input
              id="auto-delivery-schedule"
              className="text-input mono"
              value={scheduleExpression}
              placeholder="*/5 * * * *"
              aria-describedby="auto-delivery-schedule-help"
              onChange={(event) => setScheduleExpression(event.target.value)}
            />
          </div>
          <div>
            <label className="field-label" htmlFor="auto-delivery-jira-site">{t("settings.autoDeliveryJiraSite")}</label>
            <input
              id="auto-delivery-jira-site"
              className="text-input"
              value={jiraSite}
              maxLength={253}
              placeholder="team.atlassian.net"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              onChange={(event) => setJiraSite(event.target.value)}
            />
          </div>
          <div className="field-full">
            <FieldLabelWithHelp htmlFor="auto-delivery-jql" helpId="auto-delivery-jql-help"
              label={t("settings.autoDeliveryJql")} help={t("settings.autoDeliveryJqlHelp")} />
            <textarea
              id="auto-delivery-jql"
              className="text-input text-area mono"
              rows={3}
              maxLength={8000}
              value={triggerJql}
              aria-describedby="auto-delivery-jql-help"
              placeholder={'project = TEAM AND issuetype = Story AND sprint in openSprints() AND status = "To Do" AND Flagged = Impediment ORDER BY updated ASC'}
              onChange={(event) => setTriggerJql(event.target.value)}
            />
          </div>
          <div>
            <FieldLabelWithHelp htmlFor="auto-delivery-publish-mode" helpId="auto-delivery-publish-help"
              label={t("settings.autoDeliveryPublishMode")} help={t("settings.autoDeliveryPublishHelp")} />
            <select
              id="auto-delivery-publish-mode"
              className="text-input"
              value={publishMode}
              aria-describedby="auto-delivery-publish-help"
              onChange={(event) => setPublishMode(event.target.value as DeliveryPublishMode)}
            >
              <option value="local">{t("settings.autoDeliveryPublishLocal")}</option>
              <option value="branch">{t("settings.autoDeliveryPublishBranch")}</option>
              <option value="pr">{t("settings.autoDeliveryPublishPr")}</option>
              <option value="direct">{t("settings.autoDeliveryPublishDirect")}</option>
            </select>
          </div>
          {publishMode !== "local" && <div>
            <FieldLabelWithHelp htmlFor="auto-delivery-target-branch" helpId="auto-delivery-target-help"
              label={t("settings.autoDeliveryTargetBranch")} help={t("settings.autoDeliveryTargetBranchHelp")} />
            <input
              id="auto-delivery-target-branch"
              className="text-input mono"
              value={targetBranch}
              maxLength={256}
              placeholder={t("settings.autoDeliveryTargetBranchPlaceholder")}
              aria-describedby="auto-delivery-target-help"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              onChange={(event) => setTargetBranch(event.target.value)}
            />
          </div>}
          <div className="field-full">
            <label className="field-label" htmlFor="auto-delivery-hooks">
              {t("settings.autoDeliveryHooks")}
            </label>
            <textarea
              id="auto-delivery-hooks"
              className="text-input text-area"
              rows={6}
              maxLength={8000}
              value={triggerHooks}
              placeholder={t("settings.autoDeliveryHooksPlaceholder")}
              onChange={(event) => setTriggerHooks(event.target.value)}
            />
          </div>
        </div>
      </div>
      {missingTrigger && <p className="settings-description" role="status">{t("settings.autoDeliveryMissingTrigger")}</p>}
      <div className="settings-actions">
        <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || !hasChanges || missingTrigger} aria-label={`${t("settings.webhookSave")} ${t("settings.autoDelivery")}`}>
          {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}{t("settings.webhookSave")}
        </button>
      </div>
    </section>
  );
}
