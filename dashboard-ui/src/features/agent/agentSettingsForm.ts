import type { AgentSettingsUpdate, AgentReasoningEffort } from "../../shared/types";

export interface AgentSettingsDraft {
  enabled: boolean;
  defaultWorkspaceId: string;
  agentModel: string;
  agentReasoningEffort: AgentReasoningEffort;
  feishuAppId: string;
  feishuAppSecret: string;
  langfuseEnabled: boolean;
  langfuseBaseUrl: string;
  langfuseCaptureContent: boolean;
  langfuseSampleRate: string;
  langfusePublicKey: string;
  langfuseSecretKey: string;
  clearLangfuseCredentials: boolean;
}

export function buildAgentSettingsUpdate(draft: AgentSettingsDraft): AgentSettingsUpdate {
  const observability: AgentSettingsUpdate["observability"] = {
    enabled: draft.langfuseEnabled,
    base_url: draft.langfuseBaseUrl.trim(),
    capture_content: draft.langfuseCaptureContent,
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
