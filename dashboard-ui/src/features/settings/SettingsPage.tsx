import { Bell, Check, EyeOff, LoaderCircle, Save, Send, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { buildSettingsUpdate, type WebhookDraft } from "./settingsForm";
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
  const [enabled, setEnabled] = useState(settings.feishu_webhook.enabled);
  const [url, setUrl] = useState("");
  const [clearSavedUrl, setClearSavedUrl] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    setEnabled(settings.feishu_webhook.enabled);
    setUrl("");
    setClearSavedUrl(false);
    onDirtyChange(false);
  }, [settings.workspace_id, settings.feishu_webhook.enabled, settings.feishu_webhook.configured, onDirtyChange]);

  function markDirty(): void {
    onDirtyChange(true);
  }

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const saved = await onSave(buildSettingsUpdate({ enabled, url, clearSavedUrl }));
      if (!saved) return;
      onDirtyChange(false);
      setUrl("");
      setClearSavedUrl(false);
    } finally {
      setSaving(false);
    }
  }

  async function test(): Promise<void> {
    setTesting(true);
    try {
      await onTest(url.trim() || undefined);
    } finally {
      setTesting(false);
    }
  }

  const draft: WebhookDraft = { enabled, url, clearSavedUrl };
  const hasChanges = enabled !== settings.feishu_webhook.enabled || Boolean(url.trim()) || clearSavedUrl;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div><p className="eyebrow">Workspace settings</p><h1>配置</h1><p className="muted">只影响当前选中的 Workspace。</p></div>
        {hasChanges && <span className="unsaved-label">有未保存更改</span>}
      </div>

      <section className="panel settings-panel">
        <div className="panel-heading">
          <div className="settings-title"><span className="settings-icon"><Bell size={18} /></span><div><p className="eyebrow">Notifications</p><h2>飞书 Webhook</h2></div></div>
          <span className={settings.feishu_webhook.configured ? "status-pill status-ready" : "status-pill status-neutral"}>{settings.feishu_webhook.configured ? <><Check size={13} />已配置</> : "未配置"}</span>
        </div>
        <p className="settings-description">保存后，未来的工作流可以使用此 Webhook 发送通知。当前页面不会回显已保存的完整地址。</p>

        <label className="toggle-row">
          <span><strong>启用飞书通知</strong><small>允许 Lumon 的通知流程使用此配置。</small></span>
          <input type="checkbox" checked={enabled} onChange={(event) => { setEnabled(event.target.checked); markDirty(); }} />
        </label>

        <div className="form-divider" />
        <label className="field-label" htmlFor="feishu-webhook-url">Webhook URL</label>
        <div className="secret-input-wrap"><EyeOff size={16} /><input id="feishu-webhook-url" className="text-input" value={url} onChange={(event) => { setUrl(event.target.value); markDirty(); }} placeholder={settings.feishu_webhook.configured ? "已保存地址不会回显；输入新地址以替换" : "https://open.feishu.cn/open-apis/bot/v2/hook/..."} type="url" autoComplete="off" /></div>
        {settings.feishu_webhook.masked_url && <p className="field-help"><EyeOff size={14} />当前地址：<code>{settings.feishu_webhook.masked_url}</code></p>}

        <label className="clear-row"><input type="checkbox" checked={clearSavedUrl} onChange={(event) => { setClearSavedUrl(event.target.checked); markDirty(); }} /><Trash2 size={15} />清除已保存的 Webhook URL</label>

        <div className="settings-actions">
          <button className="button button-secondary" type="button" onClick={() => void test()} disabled={testing || saving || clearSavedUrl}>
            {testing ? <LoaderCircle size={16} className="spin" /> : <Send size={16} />}测试 Webhook
          </button>
          <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || testing || !hasChanges}>
            {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}保存配置
          </button>
        </div>
        <p className="security-note"><EyeOff size={14} />Webhook 地址只保存在当前用户的 Lumon profile 中，API 只返回脱敏结果。</p>
      </section>

      <section className="future-panel"><p className="eyebrow">Future settings</p><h2>可扩展配置域</h2><p>Auto Delivery 等能力会以独立的类型化设置加入，不会变成一个不可校验的通用键值编辑器。</p></section>
    </div>
  );
}

export { buildSettingsUpdate };
