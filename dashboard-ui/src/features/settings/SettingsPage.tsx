import { Bell, Check, LoaderCircle, Save, Send } from "lucide-react";
import { useEffect, useState } from "react";
import { buildSettingsUpdate } from "./settingsForm";
import { useI18n } from "../../shared/i18n";
import type { SettingsUpdate, WorkspaceSettings } from "../../shared/types";

interface SettingsPageProps {
  settings: WorkspaceSettings;
  onSave: (update: SettingsUpdate) => Promise<boolean>;
  onTest: (url?: string) => Promise<void>;
  onDirtyChange: (dirty: boolean) => void;
}

export function SettingsPage({
  settings,
  onSave,
  onTest,
  onDirtyChange,
}: SettingsPageProps): React.JSX.Element {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(settings.feishu_webhook.enabled);
  const [url, setUrl] = useState("");
  const [urlDraftActive, setUrlDraftActive] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    setEnabled(settings.feishu_webhook.enabled);
    setUrl("");
    setUrlDraftActive(false);
    onDirtyChange(false);
  }, [settings.workspace_id, settings.feishu_webhook.enabled, settings.feishu_webhook.configured, onDirtyChange]);

  function markDirty(): void {
    onDirtyChange(true);
  }

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const saved = await onSave(buildSettingsUpdate({ enabled, url }));
      if (!saved) return;
      onDirtyChange(false);
      setUrl("");
      setUrlDraftActive(false);
    } finally {
      setSaving(false);
    }
  }

  async function test(): Promise<void> {
    setTesting(true);
    try {
      await onTest(urlDraftActive && url.trim() ? url.trim() : undefined);
    } finally {
      setTesting(false);
    }
  }

  function startUrlEdit(): void {
    if (urlDraftActive) return;
    setUrlDraftActive(true);
    setUrl("");
  }

  const displayedUrl = urlDraftActive ? url : (settings.feishu_webhook.masked_url ?? "");
  const hasChanges = enabled !== settings.feishu_webhook.enabled || (urlDraftActive && Boolean(url.trim()));

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div><p className="eyebrow">{t("settings.eyebrow")}</p><h1>{t("settings.title")}</h1><p className="muted">{t("settings.subtitle")}</p></div>
        {hasChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
      </div>

      <section className="panel settings-panel">
        <div className="panel-heading">
          <div className="settings-title"><span className="settings-icon"><Bell size={18} /></span><div><p className="eyebrow">{t("settings.notifications")}</p><h2>{t("settings.feishu")}</h2></div></div>
          <div className="settings-heading-actions">
            <span className={settings.feishu_webhook.configured ? "status-pill status-ready" : "status-pill status-neutral"}>{settings.feishu_webhook.configured ? <><Check size={13} />{t("settings.configured")}</> : t("settings.notConfigured")}</span>
            <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
              <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
              <input
                type="checkbox"
                role="switch"
                checked={enabled}
                aria-label={t("settings.toggleAria")}
                onChange={(event) => { setEnabled(event.target.checked); markDirty(); }}
              />
              <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
            </label>
          </div>
        </div>
        <p className="settings-description">{t("settings.description")}</p>

        <div className={`webhook-config ${enabled ? "" : "is-disabled"}`} aria-disabled={!enabled}>
          <div className="form-divider" />
          <fieldset className="webhook-config-fields" disabled={!enabled}>
            <legend className="sr-only">{t("settings.legend")}</legend>
            <label className="field-label" htmlFor="feishu-webhook-url">{t("settings.webhookUrl")}</label>
            <input
              id="feishu-webhook-url"
              className="text-input webhook-url-input"
              value={displayedUrl}
              onFocus={startUrlEdit}
              onChange={(event) => { setUrlDraftActive(true); setUrl(event.target.value); markDirty(); }}
              placeholder={settings.feishu_webhook.configured ? t("settings.replacePlaceholder") : t("settings.newPlaceholder")}
              type="url"
              autoComplete="off"
            />
          </fieldset>
        </div>

        <div className="settings-actions">
          <button className="button button-secondary" type="button" onClick={() => void test()} disabled={testing || saving || !enabled}>
            {testing ? <LoaderCircle size={16} className="spin" /> : <Send size={16} />}{t("settings.test")}
          </button>
          <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || testing || !hasChanges}>
            {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}{t("settings.save")}
          </button>
        </div>
      </section>

      <section className="future-panel"><p className="eyebrow">{t("settings.futureEyebrow")}</p><h2>{t("settings.futureTitle")}</h2><p>{t("settings.futureCopy")}</p></section>
    </div>
  );
}

export { buildSettingsUpdate };
