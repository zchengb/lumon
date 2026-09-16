import { afterEach, describe, expect, it, vi } from "vitest";
import { dashboardApi } from "./api";

describe("Dashboard API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests a native Workspace folder selection", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ path: "/Users/me/workspace", cancelled: false }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(dashboardApi.selectWorkspaceFolder()).resolves.toEqual({
      path: "/Users/me/workspace",
      cancelled: false,
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/workspaces/select-folder", {
      method: "POST",
      headers: { Accept: "application/json" },
    });
  });

  it("loads and saves global Agent settings", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ enabled: false }),
      })
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({ enabled: true }),
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(dashboardApi.getAgentSettings()).resolves.toEqual({ enabled: false });
    await expect(
      dashboardApi.updateAgentSettings({
        enabled: true,
        default_workspace_id: null,
        agent_model: "gpt-5.6-luna",
        agent_reasoning_effort: "max",
        feishu_app_id: "cli_test",
        observability: {
          enabled: true,
          base_url: "https://cloud.langfuse.com",
          capture_content: false,
          sample_rate: 1,
        },
      }),
    ).resolves.toEqual({ enabled: true });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/agent/settings", {
      method: "PUT",
      body: JSON.stringify({
        enabled: true,
        default_workspace_id: null,
        agent_model: "gpt-5.6-luna",
        agent_reasoning_effort: "max",
        feishu_app_id: "cli_test",
        observability: {
          enabled: true,
          base_url: "https://cloud.langfuse.com",
          capture_content: false,
          sample_rate: 1,
        },
      }),
      headers: { Accept: "application/json", "Content-Type": "application/json" },
    });
  });
});
