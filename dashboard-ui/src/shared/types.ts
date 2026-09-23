export type WorkspaceHealth = "ready" | "missing" | "invalid";

export type View = "overview" | "settings" | "agent" | "auto-delivery" | "auto-scan" | "flows" | "capabilities";

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

export interface AutoDeliverySettings {
  enabled: boolean;
  trigger_hooks: string[];
  schedule_expression: string;
}

export interface AutoScanSettings {
  enabled: boolean;
  lookback_days: number;
  trigger_hooks: string[];
  schedule_expression: string;
  workflow_description: string;
}

export interface WorkspaceSettings {
  workspace_id: string;
  feishu_webhook: FeishuWebhookSettings;
  auto_delivery: AutoDeliverySettings;
  auto_scan: AutoScanSettings;
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
  auto_delivery?: {
    enabled: boolean;
    trigger_hooks?: string[];
    schedule_expression?: string;
  };
  auto_scan?: {
    enabled: boolean;
    lookback_days: number;
    trigger_hooks?: string[];
    schedule_expression?: string;
    workflow_description?: string;
  };
}

export interface ScanFinding {
  title: string;
  severity: string;
  repository: string;
  impact: string;
  trigger: string;
  file: string;
  line_range: string;
  code_snippet: string;
  suggestion: string;
  root_cause: string;
  validation: string;
  issue_id: string;
  issue_status: string;
  pr_url: string | null;
}

export interface ScanRun {
  run_id: string;
  state: string;
  phase: string;
  started_at: string;
  finished_at: string | null;
  lookback_days: number;
  repositories_scanned: number;
  repositories_failed: number;
  findings: ScanFinding[];
  failures: string[];
  hook_results: string[];
  html_available: boolean;
  pdf_available: boolean;
  duration_seconds: number | null;
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
