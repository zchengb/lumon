import { Activity, Bot, LoaderCircle, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useI18n } from "../../shared/i18n";
import type {
  AgentReasoningEffort,
  AgentSettings,
  AgentSettingsUpdate,
  WorkspaceListItem,
} from "../../shared/types";
import { buildAgentSectionUpdate, type AgentSettingsDraft, type AgentSettingsSection } from "./agentSettingsForm";
import { AgentModelPicker } from "./AgentModelPicker";
import { CodexCliNotice } from "./CodexCliNotice";

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
  const [modelRefreshVersion, setModelRefreshVersion] = useState(0);
  const [agentReasoningEffort, setAgentReasoningEffort] = useState<AgentReasoningEffort>(
    settings.agent_reasoning_effort,
  );
  const [feishuAppId, setFeishuAppId] = useState(settings.feishu_app_id);
  const [feishuAppSecret, setFeishuAppSecret] = useState("");
  const [langfuseEnabled, setLangfuseEnabled] = useState(settings.observability.enabled);
  const [langfuseBaseUrl, setLangfuseBaseUrl] = useState(settings.observability.base_url);
  const [langfusePublicKey, setLangfusePublicKey] = useState("");
  const [langfuseSecretKey, setLangfuseSecretKey] = useState("");
  const [saving, setSaving] = useState<AgentSettingsSection | null>(null);

  useEffect(() => {
    setEnabled(settings.enabled);
    setDefaultWorkspaceId(settings.default_workspace_id ?? "");
    setAgentModel(settings.agent_model);
    setAgentReasoningEffort(settings.agent_reasoning_effort);
    setFeishuAppId(settings.feishu_app_id);
    setFeishuAppSecret("");
  }, [
    settings.enabled, settings.default_workspace_id, settings.agent_model,
    settings.agent_reasoning_effort, settings.feishu_app_id, settings.feishu_app_secret_masked,
  ]);

  useEffect(() => {
    setLangfuseEnabled(settings.observability.enabled);
    setLangfuseBaseUrl(settings.observability.base_url);
    setLangfusePublicKey("");
    setLangfuseSecretKey("");
  }, [
    settings.observability.enabled, settings.observability.base_url,
    settings.observability.public_key_masked, settings.observability.secret_key_masked,
  ]);

  async function save(section: AgentSettingsSection): Promise<void> {
    if (saving !== null) return;
    setSaving(section);
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
        langfuseSampleRate: String(settings.observability.sample_rate),
        langfusePublicKey,
        langfuseSecretKey,
        clearLangfuseCredentials: false,
      };
      const saved = await onSave(buildAgentSectionUpdate(draft, settings, section));
      if (!saved) return;
      if (section === "agent") {
        setFeishuAppSecret("");
      } else {
        setLangfusePublicKey("");
        setLangfuseSecretKey("");
      }
    } finally {
      setSaving(null);
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
    Boolean(langfusePublicKey.trim()) ||
    Boolean(langfuseSecretKey.trim());
  const hasChanges = hasAgentChanges || hasLangfuseChanges;

  useEffect(() => {
    onDirtyChange(hasChanges);
  }, [hasChanges, onDirtyChange]);

  return (
    <div className="page-stack">
      <section className="panel agent-settings-panel" aria-labelledby="agent-runtime-title" aria-busy={saving === "agent"}>
        <div className="panel-heading">
          <div className="settings-title">
            <span className="workspace-glyph glyph-violet"><Bot size={18} /></span>
            <div>
              <p className="eyebrow">{t("agent.runtime")}</p>
              <h2 id="agent-runtime-title">{t("agent.title")}</h2>
            </div>
          </div>
          <div className="settings-heading-actions">
            {hasAgentChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
            <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
              <span>{enabled ? t("settings.enabled") : t("settings.disabled")}</span>
              <input
                type="checkbox"
                role="switch"
                checked={enabled}
                aria-label={t("agent.toggleAria")}
                disabled={saving === "agent"}
                onChange={(event) => setEnabled(event.target.checked)}
              />
              <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
            </label>
          </div>
        </div>
        <div className="agent-settings-body">
          <fieldset className="form-grid agent-settings-fields" disabled={saving === "agent"}>
            <legend className="sr-only">{t("agent.title")}</legend>
            <div>
              <label className="field-label" htmlFor="agent-provider">{t("agent.provider")}</label>
              <div className="text-input agent-provider-control">
                <input id="agent-provider" className="agent-provider-value" value={settings.agent_provider} readOnly />
                <CodexCliNotice modelRefresh={modelRefreshVersion} />
              </div>
            </div>
            <AgentModelPicker
              model={agentModel}
              reasoningEffort={agentReasoningEffort}
              refreshVersion={modelRefreshVersion}
              onRefresh={() => setModelRefreshVersion((previous) => previous + 1)}
              onChange={(model, effort) => { setAgentModel(model); setAgentReasoningEffort(effort); }}
            />
            <div>
              <label className="field-label" htmlFor="agent-default-workspace">{t("agent.defaultWorkspace")}</label>
              <select
                id="agent-default-workspace"
                className="text-input"
                value={defaultWorkspaceId}
                onChange={(event) => setDefaultWorkspaceId(event.target.value)}
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
                onChange={(event) => setFeishuAppId(event.target.value)}
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
                onChange={(event) => setFeishuAppSecret(event.target.value)}
                placeholder={settings.feishu_app_secret_masked ?? t("agent.secretNewPlaceholder")}
                autoComplete="new-password"
              />
            </div>
          </fieldset>
          <p className="field-help"><Activity size={14} />{t("agent.applyHelp")}</p>
          <div className="settings-actions agent-settings-actions">
            <button className="button button-primary" type="button" aria-label={`${t("agent.save")} ${t("agent.title")}`} onClick={() => void save("agent")} disabled={saving !== null || !hasAgentChanges}>
              {saving === "agent" ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
              {saving === "agent" ? t("onboarding.processing") : t("agent.save")}
            </button>
          </div>
        </div>
      </section>

      <section className="panel agent-settings-panel" aria-labelledby="agent-langfuse-title" aria-busy={saving === "langfuse"}>
        <div className="panel-heading">
          <div className="settings-title">
            <span className="workspace-glyph glyph-violet"><Activity size={18} /></span>
            <div>
              <p className="eyebrow">{t("agent.observability")}</p>
              <h2 id="agent-langfuse-title">{t("agent.langfuse")}</h2>
            </div>
          </div>
          <div className="settings-heading-actions">
            {hasLangfuseChanges && <span className="unsaved-label">{t("settings.unsaved")}</span>}
            <label className={`settings-toggle ${langfuseEnabled ? "is-enabled" : ""}`}>
              <span>{langfuseEnabled ? t("settings.enabled") : t("settings.disabled")}</span>
              <input
                type="checkbox"
                role="switch"
                checked={langfuseEnabled}
                aria-label={t("agent.langfuseToggleAria")}
                disabled={saving === "langfuse"}
                onChange={(event) => setLangfuseEnabled(event.target.checked)}
              />
              <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
            </label>
          </div>
        </div>
        <p className="settings-description">{t("agent.langfuseDescription")}</p>
        <div className="agent-settings-body">
          <fieldset className="form-grid agent-settings-fields" disabled={saving === "langfuse"}>
            <legend className="sr-only">{t("agent.langfuse")}</legend>
            <div className="field-full">
              <label className="field-label" htmlFor="langfuse-base-url">{t("agent.langfuseEndpoint")}</label>
              <input
                id="langfuse-base-url"
                className="text-input"
                type="url"
                value={langfuseBaseUrl}
                onChange={(event) => setLangfuseBaseUrl(event.target.value)}
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
                onChange={(event) => setLangfusePublicKey(event.target.value)}
                placeholder={settings.observability.public_key_masked ?? t("agent.keyNewPlaceholder")}
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="field-label" htmlFor="langfuse-secret-key">{t("agent.langfuseSecretKey")}</label>
              <input
                id="langfuse-secret-key"
                className="text-input"
                type="password"
                value={langfuseSecretKey}
                onChange={(event) => setLangfuseSecretKey(event.target.value)}
                placeholder={settings.observability.secret_key_masked ?? t("agent.keyNewPlaceholder")}
                autoComplete="new-password"
              />
            </div>
          </fieldset>
          <div className="settings-actions agent-settings-actions">
            <button className="button button-primary" type="button" aria-label={`${t("agent.save")} ${t("agent.langfuse")}`} onClick={() => void save("langfuse")} disabled={saving !== null || !hasLangfuseChanges}>
              {saving === "langfuse" ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
              {saving === "langfuse" ? t("onboarding.processing") : t("agent.save")}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
