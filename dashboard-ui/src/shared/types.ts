export type WorkspaceHealth = "ready" | "missing" | "invalid";

export type View = "overview" | "settings" | "agent" | "flows" | "capabilities";

export type AgentReasoningEffort =
  | "minimal"
  | "low"
  | "medium"
  | "high"
  | "xhigh"
  | "max"
  | "ultra";

export interface BootstrapState {
  version: string;
  workspace_count: number;
  has_workspaces: boolean;
}

export interface WorkspaceListItem {
  workspace_id: string;
  name: string;
  path: string;
  registered_at: string;
  health: WorkspaceHealth;
  detail: string;
}

export interface RepositoryOverview {
  name: string;
  path: string;
  branch: string;
  revision: string;
  health: "ready" | "unhealthy";
  detail: string;
}

export interface WorkspaceOverview {
  workspace_id: string;
  name: string;
  path: string;
  created_at: string;
  lumon_version: string;
  repositories: RepositoryOverview[];
}

export interface FeishuWebhookSettings {
  enabled: boolean;
  configured: boolean;
  masked_url: string | null;
}

export interface WorkspaceSettings {
  workspace_id: string;
  feishu_webhook: FeishuWebhookSettings;
}

export interface FlowSummary {
  flow_id: string;
  name: string;
  enabled: boolean;
  brief: string;
  path: string;
  valid: boolean;
  error: string | null;
}

export interface FlowDocument extends FlowSummary {
  content: string;
}

export interface CapabilitySummary {
  capability_id: string;
  name: string;
  enabled: boolean;
  brief: string;
  path: string;
  valid: boolean;
  error: string | null;
}

export interface CapabilityDocument extends CapabilitySummary {
  content: string;
}

export interface AgentObservabilitySettings {
  enabled: boolean;
  provider: string;
  base_url: string;
  sample_rate: number;
  public_key_configured: boolean;
  secret_key_configured: boolean;
  public_key_masked: string | null;
  secret_key_masked: string | null;
}

export interface AgentSettings {
  enabled: boolean;
  default_workspace_id: string | null;
  agent_provider: string;
  agent_model: string;
  agent_reasoning_effort: AgentReasoningEffort;
  feishu_app_id: string;
  feishu_app_configured: boolean;
  feishu_app_secret_masked: string | null;
  observability: AgentObservabilitySettings;
}

export interface SettingsUpdate {
  feishu_webhook: {
    enabled: boolean;
    url?: string;
  };
}

export interface AgentObservabilityUpdate {
  enabled: boolean;
  base_url: string;
  sample_rate: number;
  public_key?: string;
  secret_key?: string;
  clear_credentials?: boolean;
}

export interface AgentSettingsUpdate {
  enabled: boolean;
  default_workspace_id: string | null;
  agent_model: string;
  agent_reasoning_effort: AgentReasoningEffort;
  feishu_app_id: string;
  feishu_app_secret?: string;
  observability: AgentObservabilityUpdate;
}

export interface InitializeWorkspaceRequest {
  path: string;
  name?: string;
  repositories: string[];
}

export interface InitializeWorkspaceResponse {
  status: string;
  workspace: string;
  workspace_id: string;
}

export interface WorkspaceFolderSelection {
  path: string | null;
  cancelled: boolean;
}

export interface WebhookTestResponse {
  success: boolean;
  detail: string;
}
