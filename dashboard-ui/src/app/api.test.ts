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
});
