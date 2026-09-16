import { Activity, Bot, Check, KeyRound, LoaderCircle, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "../../shared/i18n";
import type {
  AgentReasoningEffort,
  AgentSettings,
  AgentSettingsUpdate,
  WorkspaceListItem,
} from "../../shared/types";
import { buildAgentSettingsUpdate, type AgentSettingsDraft } from "./agentSettingsForm";

const reasoningEfforts: readonly AgentReasoningEffort[] = [
  "minimal",
  "low",
  "medium",
  "high",
  "xhigh",
  "max",
  "ultra",
];

interface AgentSettingsPageProps {
  settings: AgentSettings;
  workspaces: WorkspaceListItem[];
  onSave: (update: AgentSettingsUpdate) => Promise<boolean>;
  onDirtyChange: (dirty: boolean) => void;
}

export function AgentSettingsPage({
  settings,
  workspaces,
  onSave,
  onDirtyChange,
}: AgentSettingsPageProps): React.JSX.Element {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(settings.enabled);
  const [defaultWorkspaceId, setDefaultWorkspaceId] = useState(settings.default_workspace_id ?? "");
  const [agentModel, setAgentModel] = useState(settings.agent_model);
  const [agentReasoningEffort, setAgentReasoningEffort] = useState<AgentReasoningEffort>(
    settings.agent_reasoning_effort,
  );
  const [feishuAppId, setFeishuAppId] = useState(settings.feishu_app_id);
  const [feishuAppSecret, setFeishuAppSecret] = useState("");
  const [langfuseEnabled, setLangfuseEnabled] = useState(settings.observability.enabled);
  const [langfuseBaseUrl, setLangfuseBaseUrl] = useState(settings.observability.base_url);
  const [langfuseCaptureContent, setLangfuseCaptureContent] = useState(
    settings.observability.capture_content,
  );
  const [langfuseSampleRate, setLangfuseSampleRate] = useState(
    String(settings.observability.sample_rate),
  );
  const [langfusePublicKey, setLangfusePublicKey] = useState("");
  const [langfuseSecretKey, setLangfuseSecretKey] = useState("");
  const [clearLangfuseCredentials, setClearLangfuseCredentials] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setEnabled(settings.enabled);
    setDefaultWorkspaceId(settings.default_workspace_id ?? "");
    setAgentModel(settings.agent_model);
    setAgentReasoningEffort(settings.agent_reasoning_effort);
    setFeishuAppId(settings.feishu_app_id);
    setFeishuAppSecret("");
    setLangfuseEnabled(settings.observability.enabled);
    setLangfuseBaseUrl(settings.observability.base_url);
    setLangfuseCaptureContent(settings.observability.capture_content);
    setLangfuseSampleRate(String(settings.observability.sample_rate));
    setLangfusePublicKey("");
    setLangfuseSecretKey("");
    setClearLangfuseCredentials(false);
    onDirtyChange(false);
  }, [onDirtyChange, settings]);

  function markDirty(): void {
    onDirtyChange(true);
  }

  async function save(): Promise<void> {
    setSaving(true);
    try {
      const draft: AgentSettingsDraft = {
        enabled,
        defaultWorkspaceId,
        agentModel,
        agentReasoningEffort,
        feishuAppId,
        feishuAppSecret,
        langfuseEnabled,
        langfuseBaseUrl,
        langfuseCaptureContent,
        langfuseSampleRate,
        langfusePublicKey,
        langfuseSecretKey,
        clearLangfuseCredentials,
      };
      await onSave(buildAgentSettingsUpdate(draft));
    } finally {
      setSaving(false);
    }
  }

  const hasAgentChanges =
    enabled !== settings.enabled ||
    defaultWorkspaceId !== (settings.default_workspace_id ?? "") ||
    agentModel.trim() !== settings.agent_model ||
    agentReasoningEffort !== settings.agent_reasoning_effort ||
    feishuAppId.trim() !== settings.feishu_app_id ||
    Boolean(feishuAppSecret.trim());
  const hasLangfuseChanges =
    langfuseEnabled !== settings.observability.enabled ||
    langfuseBaseUrl.trim() !== settings.observability.base_url ||
    langfuseCaptureContent !== settings.observability.capture_content ||
    Number.parseFloat(langfuseSampleRate) !== settings.observability.sample_rate ||
    Boolean(langfusePublicKey.trim()) ||
    Boolean(langfuseSecretKey.trim()) ||
    clearLangfuseCredentials;
  const hasChanges = hasAgentChanges || hasLangfuseChanges;
  const langfuseCredentialsConfigured =
    settings.observability.public_key_configured && settings.observability.secret_key_configured;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("agent.eyebrow")}</p>
          <h1>{t("agent.title")}</h1>
          <p className="muted">{t("agent.subtitle")}</p>
        </div>
        {hasChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
      </div>

      <section className="panel agent-settings-panel">
        <div className="panel-heading">
          <div className="settings-title">
            <span className="settings-icon"><Bot size={18} /></span>
            <div>
              <p className="eyebrow">{t("agent.runtime")}</p>
              <h2>{t("agent.title")}</h2>
            </div>
          </div>
          <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
            <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
            <input
              type="checkbox"
              role="switch"
              checked={enabled}
              aria-label={t("agent.toggleAria")}
              onChange={(event) => { setEnabled(event.target.checked); markDirty(); }}
            />
            <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
          </label>
        </div>
        <div className="agent-settings-body">
          <div className="form-grid">
            <div>
              <label className="field-label" htmlFor="agent-provider">{t("agent.provider")}</label>
              <input id="agent-provider" className="text-input" value={settings.agent_provider} readOnly />
            </div>
            <div>
              <label className="field-label" htmlFor="agent-model">{t("agent.model")}</label>
              <input
                id="agent-model"
                className="text-input"
                value={agentModel}
                onChange={(event) => { setAgentModel(event.target.value); markDirty(); }}
                autoComplete="off"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="agent-reasoning">{t("agent.reasoning")}</label>
              <select
                id="agent-reasoning"
                className="text-input"
                value={agentReasoningEffort}
                onChange={(event) => { setAgentReasoningEffort(event.target.value as AgentReasoningEffort); markDirty(); }}
              >
                {reasoningEfforts.map((effort) => <option key={effort} value={effort}>{effort}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="agent-default-workspace">{t("agent.defaultWorkspace")}</label>
              <select
                id="agent-default-workspace"
                className="text-input"
                value={defaultWorkspaceId}
                onChange={(event) => { setDefaultWorkspaceId(event.target.value); markDirty(); }}
              >
                <option value="">
                  {workspaces.length === 1 ? t("agent.autoWorkspace") : t("agent.noDefaultWorkspace")}
                </option>
                {settings.default_workspace_id && !workspaces.some((item) => item.workspace_id === settings.default_workspace_id) && (
                  <option value={settings.default_workspace_id}>{t("agent.unavailableWorkspace")}</option>
                )}
                {workspaces.map((workspace) => (
                  <option key={workspace.workspace_id} value={workspace.workspace_id}>{workspace.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="field-label" htmlFor="feishu-app-id">{t("agent.feishuAppId")}</label>
              <input
                id="feishu-app-id"
                className="text-input"
                value={feishuAppId}
                onChange={(event) => { setFeishuAppId(event.target.value); markDirty(); }}
                autoComplete="off"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="feishu-app-secret">{t("agent.feishuAppSecret")}</label>
              <input
                id="feishu-app-secret"
                className="text-input"
                type="password"
                value={feishuAppSecret}
                onChange={(event) => { setFeishuAppSecret(event.target.value); markDirty(); }}
                placeholder={settings.feishu_app_configured ? t("agent.secretReplacePlaceholder") : t("agent.secretNewPlaceholder")}
                autoComplete="new-password"
              />
              <p className="credential-status"><KeyRound size={13} />{settings.feishu_app_configured ? t("agent.secretSaved") : t("agent.secretMissing")}</p>
            </div>
          </div>
          <p className="field-help"><Activity size={14} />{t("agent.restartHelp")}</p>
        </div>
      </section>

      <section className="panel agent-settings-panel">
        <div className="panel-heading">
          <div className="settings-title">
            <span className="settings-icon"><Activity size={18} /></span>
            <div>
              <p className="eyebrow">{t("agent.observability")}</p>
              <h2>{t("agent.langfuse")}</h2>
            </div>
          </div>
          <label className={`settings-toggle ${langfuseEnabled ? "is-enabled" : ""}`}>
            <span>{langfuseEnabled ? t("settings.enabled") : t("settings.disabled")}</span>
            <input
              type="checkbox"
              role="switch"
              checked={langfuseEnabled}
              aria-label={t("agent.langfuseToggleAria")}
              onChange={(event) => { setLangfuseEnabled(event.target.checked); markDirty(); }}
            />
            <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
          </label>
        </div>
        <p className="settings-description">{t("agent.langfuseDescription")}</p>
        <div className="agent-settings-body">
          <div className="credential-summary">
            <span className={langfuseCredentialsConfigured ? "status-pill status-ready" : "status-pill status-neutral"}>
              {langfuseCredentialsConfigured && <Check size={13} />}
              {langfuseCredentialsConfigured ? t("agent.credentialsConfigured") : t("agent.credentialsMissing")}
            </span>
            <span className="muted">{t("agent.credentialsHelp")}</span>
          </div>
          <div className="form-grid">
            <div className="field-full">
              <label className="field-label" htmlFor="langfuse-base-url">{t("agent.langfuseEndpoint")}</label>
              <input
                id="langfuse-base-url"
                className="text-input"
                type="url"
                value={langfuseBaseUrl}
                onChange={(event) => { setLangfuseBaseUrl(event.target.value); markDirty(); }}
                autoComplete="url"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="langfuse-public-key">{t("agent.langfusePublicKey")}</label>
              <input
                id="langfuse-public-key"
                className="text-input"
                type="password"
                value={langfusePublicKey}
                onChange={(event) => { setLangfusePublicKey(event.target.value); setClearLangfuseCredentials(false); markDirty(); }}
                placeholder={settings.observability.public_key_configured ? t("agent.keyReplacePlaceholder") : t("agent.keyNewPlaceholder")}
                autoComplete="new-password"
                disabled={clearLangfuseCredentials}
              />
              <p className="credential-status"><KeyRound size={13} />{settings.observability.public_key_configured ? t("agent.keySaved") : t("agent.keyMissing")}</p>
            </div>
            <div>
              <label className="field-label" htmlFor="langfuse-secret-key">{t("agent.langfuseSecretKey")}</label>
              <input
                id="langfuse-secret-key"
                className="text-input"
                type="password"
                value={langfuseSecretKey}
                onChange={(event) => { setLangfuseSecretKey(event.target.value); setClearLangfuseCredentials(false); markDirty(); }}
                placeholder={settings.observability.secret_key_configured ? t("agent.keyReplacePlaceholder") : t("agent.keyNewPlaceholder")}
                autoComplete="new-password"
                disabled={clearLangfuseCredentials}
              />
              <p className="credential-status"><KeyRound size={13} />{settings.observability.secret_key_configured ? t("agent.keySaved") : t("agent.keyMissing")}</p>
            </div>
            <div>
              <label className="field-label" htmlFor="langfuse-sample-rate">{t("agent.sampleRate")}</label>
              <input
                id="langfuse-sample-rate"
                className="text-input"
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={langfuseSampleRate}
                onChange={(event) => { setLangfuseSampleRate(event.target.value); markDirty(); }}
              />
            </div>
            <label className="checkbox-row checkbox-row-panel">
              <input type="checkbox" checked={langfuseCaptureContent} onChange={(event) => { setLangfuseCaptureContent(event.target.checked); markDirty(); }} />
              <span><strong>{t("agent.captureContent")}</strong><small>{t("agent.captureContentHelp")}</small></span>
            </label>
          </div>
          {langfuseCredentialsConfigured && (
            <label className="checkbox-row">
              <input type="checkbox" checked={clearLangfuseCredentials} onChange={(event) => { setClearLangfuseCredentials(event.target.checked); setLangfusePublicKey(""); setLangfuseSecretKey(""); markDirty(); }} />
              <span>{t("agent.clearLangfuseCredentials")}</span>
            </label>
          )}
        </div>
      </section>

      <div className="settings-actions agent-settings-actions">
        <button className="button button-primary" type="button" onClick={() => void save()} disabled={saving || !hasChanges}>
          {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
          {saving ? t("onboarding.processing") : t("agent.save")}
        </button>
      </div>
    </div>
  );
}
