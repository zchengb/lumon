import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { I18nProvider } from "../shared/i18n";
import type { AgentSettings, WorkspaceListItem, WorkspaceSettings } from "../shared/types";
import { dashboardApi } from "./api";
import { App } from "./App";

const workspaces: WorkspaceListItem[] = ["workspace-one", "workspace-two"].map((workspace_id) => ({
  workspace_id, name: workspace_id, path: "/test", registered_at: "2026-09-30T04:00:00Z", health: "ready", detail: "",
}));
const agent: AgentSettings = {
  enabled: true, default_workspace_id: "workspace-one", agent_provider: "codex", agent_model: "gpt-5.6-luna",
  agent_reasoning_effort: "max", feishu_app_id: "cli_test", feishu_app_configured: true,
  feishu_app_secret_masked: "abcd…wxyz", observability: {
    enabled: true, provider: "langfuse", base_url: "https://cloud.langfuse.com", sample_rate: 1,
    public_key_configured: true, secret_key_configured: true, public_key_masked: "pk…1234", secret_key_masked: "sk…5678",
  },
};
const settings: WorkspaceSettings = {
  workspace_id: "workspace-one", feishu_webhook: { enabled: true, configured: true, masked_url: "https://example.test/…1234" },
  auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "" },
  auto_scan: { enabled: false, lookback_days: 7, trigger_hooks: [], schedule_expression: "", workflow_description: "" },
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); window.history.replaceState(null, "", "/"); });

it("merges history into Agent, moves global configuration to Settings and protects both settings drafts", async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  window.history.replaceState(null, "", "?workspace=workspace-one&view=chat-history");
  vi.spyOn(dashboardApi, "listWorkspaces").mockResolvedValue(workspaces);
  vi.spyOn(dashboardApi, "getBootstrap").mockResolvedValue({ version: "1.4.7", workspace_count: 2, has_workspaces: true });
  vi.spyOn(dashboardApi, "getAgentSettings").mockResolvedValue(agent);
  vi.spyOn(dashboardApi, "listAgentModels").mockResolvedValue(["gpt-5.6-luna", "gpt-test"].map((model) => ({
    model, display_name: model, description: "", default_reasoning_effort: "max", supported_reasoning_efforts: ["max"],
  })));
  vi.spyOn(dashboardApi, "getSettings").mockImplementation(async (workspaceId) => ({ ...settings, workspace_id: workspaceId }));
  vi.spyOn(dashboardApi, "getOverview").mockImplementation(async (workspaceId) => ({
    workspace_id: workspaceId, name: workspaceId, path: "/test", created_at: "2026-09-30T04:00:00Z", lumon_version: "1.4.7", repositories: [],
  }));
  vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [], total: 0 });
  const saveAgent = vi.spyOn(dashboardApi, "updateAgentSettings").mockImplementation(async (update) => ({ ...agent, agent_model: update.agent_model }));
  const saveWebhook = vi.spyOn(dashboardApi, "updateSettings").mockResolvedValue(settings);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const container = document.createElement("div");
  const root = createRoot(container);
  function navigation(label: string): HTMLButtonElement {
    return container.querySelector<HTMLButtonElement>(`.side-nav button[aria-label="${label}"]`)!;
  }
  async function edit(selector: string, text: string): Promise<void> {
    await act(async () => {
      const field = container.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!;
      if (field instanceof HTMLSelectElement) {
        field.value = text;
        field.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(field, text);
        field.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
  }
  try {
    await act(async () => root.render(<I18nProvider><App /></I18nProvider>));
    expect(window.location.search).toContain("view=agent");
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(container.querySelector("h1")?.textContent).toBe("Agent");
    expect(container.querySelector("#agent-model")).toBeNull();
    expect(container.querySelectorAll(".side-nav button")).toHaveLength(7);
    expect(container.querySelector(".side-nav")?.textContent).not.toContain("Conversation history");

    await act(async () => navigation("Settings").click());
    expect(container.querySelectorAll("h1")).toHaveLength(1);
    expect(container.querySelector("#feishu-webhook-url")).not.toBeNull();
    expect(container.querySelector("#agent-model")).not.toBeNull();
    expect(container.querySelector("#langfuse-base-url")).not.toBeNull();
    expect(container.querySelector(".settings-panel .status-pill")).toBeNull();
    expect(container.textContent).not.toContain("Global Agent settings");
    expect(container.textContent).not.toContain("Applies to the local Agent across all Workspaces.");
    expect(container.querySelectorAll('[role="switch"]')).toHaveLength(3);
    expect(container.querySelector<HTMLInputElement>("#feishu-webhook-url")?.value).toBe("https://example.test/…1234");
    expect(container.querySelector<HTMLInputElement>("#feishu-app-secret")?.placeholder).toBe("abcd…wxyz");

    await edit("#agent-model", "gpt-test");
    expect(container.querySelector(".agent-settings-panel .unsaved-label")?.textContent).toBe("Unsaved changes");
    await act(async () => navigation("Agent").click());
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(container.querySelector("h1")?.textContent).toBe("Settings");
    await act(async () => {
      const picker = container.querySelector<HTMLSelectElement>(".workspace-picker select")!;
      picker.value = "workspace-two";
      picker.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(window.location.search).toContain("workspace=workspace-one");
    await act(async () => container.querySelector<HTMLButtonElement>(".agent-settings-actions button")!.click());
    expect(saveAgent).toHaveBeenCalledWith(expect.objectContaining({ agent_model: "gpt-test" }));
    expect(saveAgent.mock.calls[0][0].feishu_app_secret).toBeUndefined();
    expect(saveAgent.mock.calls[0][0].observability.secret_key).toBeUndefined();
    expect(saveWebhook).not.toHaveBeenCalled();

    await edit("#feishu-webhook-url", "https://example.test/replacement");
    await act(async () => navigation("Agent").click());
    expect(confirm).toHaveBeenCalledTimes(3);
    confirm.mockReturnValue(true);
    await act(async () => navigation("Agent").click());
    expect(container.querySelector("#agent-model")).toBeNull();
    expect(container.querySelector("h1")?.textContent).toBe("Agent");
  } finally {
    await act(async () => root.unmount());
  }
});
