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
          sample_rate: 1,
        },
      }),
      headers: { Accept: "application/json", "Content-Type": "application/json" },
    });
  });

  it("uses the Workspace flow CRUD endpoints", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify([{ flow_id: "sample" }]) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ flow_id: "sample", content: "old" }) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ flow_id: "created", content: "new" }) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ flow_id: "created", content: "saved" }) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ flow_id: "created", schedule_enabled: true }) })
      .mockResolvedValueOnce({ ok: true, text: async () => "" });
    vi.stubGlobal("fetch", fetchMock);

    await dashboardApi.listFlows("workspace-1");
    await dashboardApi.getFlow("workspace-1", "sample");
    await dashboardApi.createFlow("workspace-1", "new");
    await dashboardApi.updateFlow("workspace-1", "created", "saved");
    await dashboardApi.updateFlowSchedule("workspace-1", "created", true, "0 8 * * 1-5");
    await dashboardApi.deleteFlow("workspace-1", "created");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/workspaces/workspace-1/flows", {
      headers: { Accept: "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/workspaces/workspace-1/flows/sample", {
      headers: { Accept: "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/workspaces/workspace-1/flows", {
      method: "POST",
      body: JSON.stringify({ content: "new" }),
      headers: { Accept: "application/json", "Content-Type": "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/workspaces/workspace-1/flows/created",
      {
        method: "PUT",
        body: JSON.stringify({ content: "saved" }),
        headers: { Accept: "application/json", "Content-Type": "application/json" },
      },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/workspaces/workspace-1/flows/created/schedule", {
      method: "PUT",
      body: JSON.stringify({ enabled: true, schedule_expression: "0 8 * * 1-5" }),
      headers: { Accept: "application/json", "Content-Type": "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(6, "/api/workspaces/workspace-1/flows/created", {
      method: "DELETE",
      headers: { Accept: "application/json" },
    });
  });

  it("uses the Workspace capability CRUD endpoints", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify([{ capability_id: "sample" }]) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ capability_id: "sample", content: "old" }) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ capability_id: "created", content: "new" }) })
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ capability_id: "created", content: "saved" }) })
      .mockResolvedValueOnce({ ok: true, text: async () => "" });
    vi.stubGlobal("fetch", fetchMock);

    await dashboardApi.listCapabilities("workspace-1");
    await dashboardApi.getCapability("workspace-1", "sample");
    await dashboardApi.createCapability("workspace-1", "new");
    await dashboardApi.updateCapability("workspace-1", "created", "saved");
    await dashboardApi.deleteCapability("workspace-1", "created");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/workspaces/workspace-1/capabilities", {
      headers: { Accept: "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/workspaces/workspace-1/capabilities/sample", {
      headers: { Accept: "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/workspaces/workspace-1/capabilities", {
      method: "POST",
      body: JSON.stringify({ content: "new" }),
      headers: { Accept: "application/json", "Content-Type": "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "/api/workspaces/workspace-1/capabilities/created",
      {
        method: "PUT",
        body: JSON.stringify({ content: "saved" }),
        headers: { Accept: "application/json", "Content-Type": "application/json" },
      },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(5, "/api/workspaces/workspace-1/capabilities/created", {
      method: "DELETE",
      headers: { Accept: "application/json" },
    });
  });
});
