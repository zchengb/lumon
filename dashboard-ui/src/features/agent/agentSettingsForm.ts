import type { AgentSettings, AgentSettingsUpdate, AgentReasoningEffort } from "../../shared/types";

export type AgentSettingsSection = "agent" | "langfuse";

export interface AgentSettingsDraft {
  enabled: boolean;
  defaultWorkspaceId: string;
  agentModel: string;
  agentReasoningEffort: AgentReasoningEffort;
  feishuAppId: string;
  feishuAppSecret: string;
  langfuseEnabled: boolean;
  langfuseBaseUrl: string;
  langfuseSampleRate: string;
  langfusePublicKey: string;
  langfuseSecretKey: string;
  clearLangfuseCredentials: boolean;
}

export function buildAgentSettingsUpdate(draft: AgentSettingsDraft): AgentSettingsUpdate {
  const observability: AgentSettingsUpdate["observability"] = {
    enabled: draft.langfuseEnabled,
    base_url: draft.langfuseBaseUrl.trim(),
    sample_rate: Number(draft.langfuseSampleRate),
    clear_credentials: draft.clearLangfuseCredentials,
  };
  if (draft.langfusePublicKey.trim()) observability.public_key = draft.langfusePublicKey.trim();
  if (draft.langfuseSecretKey.trim()) observability.secret_key = draft.langfuseSecretKey.trim();

  const update: AgentSettingsUpdate = {
    enabled: draft.enabled,
    default_workspace_id: draft.defaultWorkspaceId.trim() || null,
    agent_model: draft.agentModel.trim(),
    agent_reasoning_effort: draft.agentReasoningEffort,
    feishu_app_id: draft.feishuAppId.trim(),
    observability,
  };
  if (draft.feishuAppSecret.trim()) update.feishu_app_secret = draft.feishuAppSecret.trim();
  return update;
}

export function buildAgentSectionUpdate(
  draft: AgentSettingsDraft,
  settings: AgentSettings,
  section: AgentSettingsSection,
): AgentSettingsUpdate {
  const update = buildAgentSettingsUpdate(draft);
  if (section === "agent") {
    return {
      ...update,
      observability: {
        enabled: settings.observability.enabled,
        base_url: settings.observability.base_url,
        sample_rate: settings.observability.sample_rate,
      },
    };
  }
  return {
    enabled: settings.enabled,
    default_workspace_id: settings.default_workspace_id,
    agent_model: settings.agent_model,
    agent_reasoning_effort: settings.agent_reasoning_effort,
    feishu_app_id: settings.feishu_app_id,
    observability: update.observability,
  };
}
