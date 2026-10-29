import type {
  AgentModel,
  AgentSettings,
  AgentSettingsUpdate,
  BootstrapState,
  CapabilityDocument,
  CapabilitySummary,
  ChatInteractionDetail,
  ChatInteractionPage,
  ChatKind,
  CodexCliStatus,
  DeliveryActivity,
  DeliveryHistory,
  FlowDocument,
  FlowSummary,
  InitializeWorkspaceRequest,
  InitializeWorkspaceResponse,
  RemoteRepository,
  McpCreate,
  McpDiscovery,
  McpInventory,
  SettingsUpdate,
  SetupReport,
  WebhookTestResponse,
  WorkspaceFolderSelection,
  WorkspaceListItem,
  WorkspaceOverview,
  WorkspaceSettings,
  ScanRun,
  VisualEnvironmentSnapshot,
} from "../shared/types";

interface ErrorPayload {
  error?: {
    message?: unknown;
  };
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text) as unknown;
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const errorPayload = payload as ErrorPayload | null;
    const message =
      typeof errorPayload?.error?.message === "string"
        ? errorPayload.error.message
        : `Dashboard request failed (${response.status}).`;
    throw new ApiError(response.status, message);
  }
  return payload as T;
}

export const dashboardApi = {
  getSetup(): Promise<SetupReport> {
    return request("/api/setup", { cache: "no-store" });
  },
  repositoryOrganizations(host: string, page = 1): Promise<string[]> {
    return request("/api/repository-sources/organizations", { method: "POST", body: JSON.stringify({ host, page }) });
  },
  sourceRepositoryBranches(host: string, repository: string, page = 1): Promise<string[]> {
    return request("/api/repository-sources/branches", { method: "POST", body: JSON.stringify({ host, repository, page }) });
  },
  repositorySources(): Promise<string[]> {
    return request("/api/repository-sources", { cache: "no-store" });
  },
  searchRepositories(host: string, query: string, page = 1, organization = ""): Promise<RemoteRepository[]> {
    return request("/api/repository-sources/search", {
      method: "POST", body: JSON.stringify({ host, query, page, ...(organization ? { organization } : {}) }),
    });
  },
  addRepositories(workspaceId: string, expectedVersion: string, repositories: RemoteRepository[]): Promise<void> {
    return request(`/api/workspaces/${workspaceId}/repositories`, {
      method: "POST", body: JSON.stringify({ expected_version: expectedVersion, repositories }),
    });
  },
  updateRepositoryScopes(workspaceId: string, version: string, repositories: { name: string; auto_scan: boolean; auto_delivery: boolean }[]): Promise<{ repositories_version: string }> {
    return request(`/api/workspaces/${workspaceId}/repositories/scope`, {
      method: "PUT", body: JSON.stringify({ expected_version: version, repositories }),
    });
  },
  repositoryBranches(workspaceId: string, name: string): Promise<string[]> {
    return request(`/api/workspaces/${workspaceId}/repositories/${encodeURIComponent(name)}/branches`, { cache: "no-store" });
  },
  updateRepositoryBranch(workspaceId: string, name: string, version: string, branch: string): Promise<{ repositories_version: string }> {
    return request(`/api/workspaces/${workspaceId}/repositories/${encodeURIComponent(name)}/branch`, {
      method: "PUT", body: JSON.stringify({ expected_version: version, branch }),
    });
  },
  listMcp(workspaceId: string): Promise<McpInventory> {
    return request(`/api/workspaces/${workspaceId}/mcp`, { cache: "no-store" });
  },
  addMcp(workspaceId: string, payload: McpCreate): Promise<void> {
    return request(`/api/workspaces/${workspaceId}/mcp`, { method: "POST", body: JSON.stringify(payload) });
  },
  discoverMcp(workspaceId: string, name: string): Promise<McpDiscovery> {
    return request(`/api/workspaces/${workspaceId}/mcp/${encodeURIComponent(name)}/discover`, { method: "POST" });
  },
  setMcpEnabled(workspaceId: string, name: string, enabled: boolean, expectedVersion: string | null): Promise<void> {
    return request(`/api/workspaces/${workspaceId}/mcp/${encodeURIComponent(name)}`, { method: "PUT", body: JSON.stringify({ enabled, expected_version: expectedVersion }) });
  },
  removeMcp(workspaceId: string, name: string, expectedVersion: string | null): Promise<void> {
    return request(`/api/workspaces/${workspaceId}/mcp/${encodeURIComponent(name)}/remove`, { method: "POST", body: JSON.stringify({ expected_version: expectedVersion }) });
  },
  controlDelivery(workspaceId: string, runId: string, action: "resume" | "stop", attempt: number): Promise<{ accepted: boolean }> {
    return request(`/api/workspaces/${workspaceId}/deliveries/${encodeURIComponent(runId)}/${action}`, { method: "POST", body: JSON.stringify({ attempt }) });
  },
  getVisualEnvironment(workspaceId: string, refresh = false): Promise<VisualEnvironmentSnapshot> {
    return request<VisualEnvironmentSnapshot>(`/api/workspaces/${workspaceId}/environment?refresh=${refresh}`, { cache: "no-store" });
  },
  getDeliveryHistory(workspaceId: string): Promise<DeliveryHistory> {
    return request<DeliveryHistory>(`/api/workspaces/${workspaceId}/deliveries`, { cache: "no-store" });
  },

  deleteDeliveryHistory(workspaceId: string, runId: string): Promise<void> {
    return request<void>(`/api/workspaces/${workspaceId}/deliveries/${encodeURIComponent(runId)}`, { method: "DELETE" });
  },

  getDeliveryActivity(workspaceId: string, runId: string): Promise<DeliveryActivity[]> {
    return request<DeliveryActivity[]>(`/api/workspaces/${workspaceId}/deliveries/${encodeURIComponent(runId)}/activity`, { cache: "no-store" });
  },
  getBootstrap(): Promise<BootstrapState> {
    return request<BootstrapState>("/api/bootstrap");
  },

  getAgentSettings(): Promise<AgentSettings> {
    return request<AgentSettings>("/api/agent/settings");
  },

  listAgentModels(): Promise<AgentModel[]> {
    return request<AgentModel[]>("/api/agent/models", { cache: "no-store" });
  },

  getCodexCliStatus(refresh = false): Promise<CodexCliStatus> {
    const query = refresh ? "?refresh=true" : "";
    return request<CodexCliStatus>(`/api/agent/codex-status${query}`, { cache: "no-store" });
  },

  listConversations(workspaceId: string, kind: ChatKind, search: string, offset: number): Promise<ChatInteractionPage> {
    const query = new URLSearchParams({ kind, search, offset: String(offset), limit: "20" });
    return request<ChatInteractionPage>(`/api/workspaces/${workspaceId}/conversations?${query}`);
  },

  getConversation(workspaceId: string, runId: string): Promise<ChatInteractionDetail> {
    return request<ChatInteractionDetail>(`/api/workspaces/${workspaceId}/conversations/${encodeURIComponent(runId)}`);
  },

  updateAgentSettings(payload: AgentSettingsUpdate): Promise<AgentSettings> {
    return request<AgentSettings>("/api/agent/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  listWorkspaces(): Promise<WorkspaceListItem[]> {
    return request<WorkspaceListItem[]>("/api/workspaces");
  },

  selectWorkspaceFolder(): Promise<WorkspaceFolderSelection> {
    return request<WorkspaceFolderSelection>("/api/workspaces/select-folder", {
      method: "POST",
    });
  },

  registerWorkspace(path: string): Promise<WorkspaceListItem> {
    return request<WorkspaceListItem>("/api/workspaces/register", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
  },

  initializeWorkspace(
    payload: InitializeWorkspaceRequest,
  ): Promise<InitializeWorkspaceResponse> {
    return request<InitializeWorkspaceResponse>("/api/workspaces/initialize", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getOverview(workspaceId: string): Promise<WorkspaceOverview> {
    return request<WorkspaceOverview>(`/api/workspaces/${workspaceId}/overview`);
  },

  getSettings(workspaceId: string): Promise<WorkspaceSettings> {
    return request<WorkspaceSettings>(`/api/workspaces/${workspaceId}/settings`);
  },

  listFlows(workspaceId: string): Promise<FlowSummary[]> {
    return request<FlowSummary[]>(`/api/workspaces/${workspaceId}/flows`);
  },

  getFlow(workspaceId: string, flowId: string): Promise<FlowDocument> {
    return request<FlowDocument>(`/api/workspaces/${workspaceId}/flows/${encodeURIComponent(flowId)}`);
  },

  createFlow(workspaceId: string, content: string): Promise<FlowDocument> {
    return request<FlowDocument>(`/api/workspaces/${workspaceId}/flows`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  updateFlow(workspaceId: string, flowId: string, content: string): Promise<FlowDocument> {
    return request<FlowDocument>(
      `/api/workspaces/${workspaceId}/flows/${encodeURIComponent(flowId)}`,
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      },
    );
  },

  updateFlowSchedule(
    workspaceId: string,
    flowId: string,
    enabled: boolean,
    scheduleExpression: string,
  ): Promise<FlowDocument> {
    return request<FlowDocument>(
      `/api/workspaces/${workspaceId}/flows/${encodeURIComponent(flowId)}/schedule`,
      {
        method: "PUT",
        body: JSON.stringify({ enabled, schedule_expression: scheduleExpression }),
      },
    );
  },

  deleteFlow(workspaceId: string, flowId: string): Promise<void> {
    return request<void>(`/api/workspaces/${workspaceId}/flows/${encodeURIComponent(flowId)}`, {
      method: "DELETE",
    });
  },

  runFlow(workspaceId: string, flowId: string): Promise<{ flow_id: string; status: "completed" }> {
    return request(`/api/workspaces/${workspaceId}/flows/${encodeURIComponent(flowId)}/run`, {
      method: "POST",
    });
  },

  listCapabilities(workspaceId: string): Promise<CapabilitySummary[]> {
    return request<CapabilitySummary[]>("/api/workspaces/" + workspaceId + "/capabilities");
  },

  getCapability(workspaceId: string, capabilityId: string): Promise<CapabilityDocument> {
    return request<CapabilityDocument>(
      "/api/workspaces/"
      + workspaceId
      + "/capabilities/"
      + encodeURIComponent(capabilityId),
    );
  },

  createCapability(workspaceId: string, content: string): Promise<CapabilityDocument> {
    return request<CapabilityDocument>(
      "/api/workspaces/" + workspaceId + "/capabilities",
      {
        method: "POST",
        body: JSON.stringify({ content }),
      },
    );
  },

  updateCapability(
    workspaceId: string,
    capabilityId: string,
    content: string,
  ): Promise<CapabilityDocument> {
    return request<CapabilityDocument>(
      "/api/workspaces/"
      + workspaceId
      + "/capabilities/"
      + encodeURIComponent(capabilityId),
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      },
    );
  },

  deleteCapability(workspaceId: string, capabilityId: string): Promise<void> {
    return request<void>(
      "/api/workspaces/"
      + workspaceId
      + "/capabilities/"
      + encodeURIComponent(capabilityId),
      { method: "DELETE" },
    );
  },

  updateSettings(workspaceId: string, payload: SettingsUpdate): Promise<WorkspaceSettings> {
    return request<WorkspaceSettings>(`/api/workspaces/${workspaceId}/settings`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  listScans(workspaceId: string): Promise<ScanRun[]> {
    return request<ScanRun[]>(`/api/workspaces/${workspaceId}/scans`);
  },

  startScan(workspaceId: string): Promise<ScanRun> {
    return request<ScanRun>(`/api/workspaces/${workspaceId}/scans`, { method: "POST" });
  },

  ignoreScanFinding(workspaceId: string, runId: string, findingIndex: number): Promise<ScanRun[]> {
    return request<ScanRun[]>(`/api/workspaces/${workspaceId}/scans/${encodeURIComponent(runId)}/findings/${findingIndex}/ignore`, { method: "POST", body: JSON.stringify({ ignored: true }) });
  },

  testFeishu(workspaceId: string, url?: string): Promise<WebhookTestResponse> {
    return request<WebhookTestResponse>(
      `/api/workspaces/${workspaceId}/settings/feishu/test`,
      {
        method: "POST",
        body: JSON.stringify(url ? { url } : {}),
      },
    );
  },
};
