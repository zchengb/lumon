export type WorkspaceHealth = "ready" | "missing" | "invalid";

export type View = "overview" | "settings";

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

export interface SettingsUpdate {
  feishu_webhook: {
    enabled: boolean;
    url?: string;
  };
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

export interface WebhookTestResponse {
  success: boolean;
  detail: string;
}
