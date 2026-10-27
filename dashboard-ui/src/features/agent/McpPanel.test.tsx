import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { McpInventory } from "../../shared/types";
import { McpPanel } from "./McpPanel";

const inventory: McpInventory = { user_version: "v1", servers: [
  { name: "figma", enabled: true, transport: "http", auth_status: "unknown", source: "user", manageable: true, description_kind: "figma" },
  { name: "plugin", enabled: true, transport: "stdio", auth_status: "unsupported", source: "other", manageable: false, description_kind: null },
] };

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "listMcp").mockResolvedValue(inventory);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

it("shows an official description without claiming a connection", async () => {
  const element = document.createElement("div");
  const root = createRoot(element);
  try {
    await act(async () => root.render(<I18nProvider><McpPanel workspaceId="one" /></I18nProvider>));
    expect(element.textContent).toContain("2 / 2 enabled");
    expect(element.textContent).toContain("Provides Figma design context");
    expect(element.textContent).not.toContain("Connected");
  } finally { await act(async () => root.unmount()); }
});

it("checks one catalog and changes only user-managed servers with the expected version", async () => {
  vi.spyOn(dashboardApi, "discoverMcp").mockResolvedValue({ auth_status: "oAuth", runtime_status: null, tools: ["read_design"], total_tools: 1, failed: false, description: "The server's own description." });
  vi.spyOn(dashboardApi, "setMcpEnabled").mockResolvedValue();
  vi.spyOn(dashboardApi, "removeMcp").mockResolvedValue();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const element = document.createElement("div");
  const root = createRoot(element);
  try {
    await act(async () => root.render(<I18nProvider><McpPanel workspaceId="one" /></I18nProvider>));
    const rows = element.querySelectorAll<HTMLLIElement>(".mcp-row");
    expect(rows[1].querySelector<HTMLInputElement>('input[role="switch"]')?.disabled).toBe(true);
    await act(async () => rows[0].querySelector<HTMLButtonElement>(".mcp-row-actions button")!.click());
    expect(dashboardApi.discoverMcp).toHaveBeenCalledWith("one", "figma");
    expect(rows[0].textContent).toContain("Tool catalog read; connection state is unconfirmed.");
    expect(rows[0].textContent).toContain("read_design");
    expect(rows[0].textContent).toContain("The server's own description.");
    await act(async () => rows[0].querySelector<HTMLInputElement>('input[role="switch"]')!.click());
    expect(dashboardApi.setMcpEnabled).toHaveBeenCalledWith("one", "figma", false, "v1");
    await act(async () => rows[0].querySelector<HTMLButtonElement>(".mcp-remove")!.click());
    expect(dashboardApi.removeMcp).toHaveBeenCalledWith("one", "figma", "v1");
  } finally { await act(async () => root.unmount()); }
});

it("refreshes after an unconfirmed configuration write", async () => {
  vi.spyOn(dashboardApi, "setMcpEnabled").mockRejectedValue(new Error("network failure"));
  const element = document.createElement("div");
  const root = createRoot(element);
  try {
    await act(async () => root.render(<I18nProvider><McpPanel workspaceId="one" /></I18nProvider>));
    await act(async () => element.querySelector<HTMLInputElement>('input[role="switch"]')!.click());
    expect(dashboardApi.listMcp).toHaveBeenCalledTimes(2);
    expect(element.querySelector('[role="alert"]')?.textContent).toContain("settings may have changed");
  } finally { await act(async () => root.unmount()); }
});

it("adds an HTTP server without placing a credential in the request", async () => {
  vi.spyOn(dashboardApi, "addMcp").mockResolvedValue();
  const element = document.createElement("div");
  const root = createRoot(element);
  try {
    await act(async () => root.render(<I18nProvider><McpPanel workspaceId="one" /></I18nProvider>));
    await act(async () => element.querySelector<HTMLButtonElement>(".mcp-add-area button")!.click());
    const inputs = element.querySelectorAll<HTMLInputElement>(".mcp-form input");
    await act(async () => {
      for (const [input, value] of [[inputs[0], "docs"], [inputs[1], "https://example.com/mcp"], [inputs[2], "MCP_TOKEN"]] as const) {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
    await act(async () => element.querySelector<HTMLFormElement>(".mcp-form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(dashboardApi.addMcp).toHaveBeenCalledWith("one", {
      name: "docs", transport: "http", url: "https://example.com/mcp", bearer_token_env_var: "MCP_TOKEN", expected_version: "v1",
    });
  } finally { await act(async () => root.unmount()); }
});
