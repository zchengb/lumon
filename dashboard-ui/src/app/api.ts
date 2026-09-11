import type {
  BootstrapState,
  InitializeWorkspaceRequest,
  InitializeWorkspaceResponse,
  SettingsUpdate,
  WebhookTestResponse,
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

  listWorkspaces(): Promise<WorkspaceListItem[]> {
    return request<WorkspaceListItem[]>("/api/workspaces");
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
