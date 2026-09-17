import type {
  AgentSettings,
  AgentSettingsUpdate,
  BootstrapState,
  FlowDocument,
  FlowSummary,
  InitializeWorkspaceRequest,
  InitializeWorkspaceResponse,
  SettingsUpdate,
  WebhookTestResponse,
  WorkspaceFolderSelection,
  WorkspaceListItem,
  WorkspaceOverview,
  WorkspaceSettings,
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
  getBootstrap(): Promise<BootstrapState> {
    return request<BootstrapState>("/api/bootstrap");
  },

  getAgentSettings(): Promise<AgentSettings> {
    return request<AgentSettings>("/api/agent/settings");
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

  deleteFlow(workspaceId: string, flowId: string): Promise<void> {
    return request<void>(`/api/workspaces/${workspaceId}/flows/${encodeURIComponent(flowId)}`, {
      method: "DELETE",
    });
  },

  updateSettings(workspaceId: string, payload: SettingsUpdate): Promise<WorkspaceSettings> {
    return request<WorkspaceSettings>(`/api/workspaces/${workspaceId}/settings`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
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
