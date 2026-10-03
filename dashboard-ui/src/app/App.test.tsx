import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { I18nProvider } from "../shared/i18n";
import type { AgentSettings, FlowDocument, WorkspaceListItem, WorkspaceSettings } from "../shared/types";
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
  vi.spyOn(dashboardApi, "getBootstrap").mockResolvedValue({ version: "1.4.9", workspace_count: 2, has_workspaces: true });
  vi.spyOn(dashboardApi, "getAgentSettings").mockResolvedValue(agent);
  vi.spyOn(dashboardApi, "getCodexCliStatus").mockResolvedValue({
    status: "up_to_date", binary_path: "/test/codex", installed_version: "0.160.0", latest_version: "0.160.0",
  });
  vi.spyOn(dashboardApi, "listAgentModels").mockResolvedValue(["gpt-5.6-luna", "gpt-test"].map((model) => ({
    model, display_name: model, description: "", default_reasoning_effort: "max", supported_reasoning_efforts: ["max"],
  })));
  vi.spyOn(dashboardApi, "getSettings").mockImplementation(async (workspaceId) => ({ ...settings, workspace_id: workspaceId }));
  vi.spyOn(dashboardApi, "getOverview").mockImplementation(async (workspaceId) => ({
    workspace_id: workspaceId, name: workspaceId, path: "/test", created_at: "2026-09-30T04:00:00Z", lumon_version: "1.4.9", repositories: [], workflow_schedules: [],
  }));
  vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [], total: 0 });
  const saveAgent = vi.spyOn(dashboardApi, "updateAgentSettings").mockImplementation(async (update) => ({
    ...agent, agent_model: update.agent_model, observability: { ...agent.observability, ...update.observability },
  }));
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
    await edit("#langfuse-base-url", "https://draft.langfuse.test");
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
    expect(saveAgent.mock.calls[0][0].observability.base_url).toBe(agent.observability.base_url);
    expect(saveWebhook).not.toHaveBeenCalled();
    expect(container.querySelector<HTMLInputElement>("#langfuse-base-url")?.value).toBe("https://draft.langfuse.test");
    await act(async () => navigation("Agent").click());
    expect(confirm).toHaveBeenCalledTimes(3);
    expect(container.querySelector("h1")?.textContent).toBe("Settings");
    await act(async () => container.querySelector<HTMLButtonElement>('button[aria-label="Save Langfuse Cloud"]')!.click());
    expect(saveAgent).toHaveBeenLastCalledWith(expect.objectContaining({
      agent_model: "gpt-test", observability: expect.objectContaining({ base_url: "https://draft.langfuse.test" }),
    }));

    await edit("#feishu-webhook-url", "https://example.test/replacement");
    await act(async () => navigation("Agent").click());
    expect(confirm).toHaveBeenCalledTimes(4);
    confirm.mockReturnValue(true);
    await act(async () => navigation("Agent").click());
    expect(container.querySelector("#agent-model")).toBeNull();
    expect(container.querySelector("h1")?.textContent).toBe("Agent");
  } finally {
    await act(async () => root.unmount());
  }
});

it("opens a scheduled workflow, reloads its saved schedule on return, and isolates workspaces", async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  window.history.replaceState(null, "", "?workspace=workspace-one&view=overview");
  let flow: FlowDocument = {
    flow_id: "auto-guard", name: "Auto Guard", enabled: true, brief: "Inspect production.", path: "lumon/flows/auto-guard.md",
    valid: true, error: null, content: "# Auto Guard", schedule_enabled: true, schedule_expression: "0 10 * * 1-5",
  };
  vi.spyOn(dashboardApi, "listWorkspaces").mockResolvedValue(workspaces);
  vi.spyOn(dashboardApi, "getBootstrap").mockResolvedValue({ version: "1.4.10", workspace_count: 2, has_workspaces: true });
  vi.spyOn(dashboardApi, "getAgentSettings").mockResolvedValue(agent);
  vi.spyOn(dashboardApi, "getSettings").mockImplementation(async (workspaceId) => ({ ...settings, workspace_id: workspaceId }));
  const overview = vi.spyOn(dashboardApi, "getOverview").mockImplementation(async (workspaceId) => ({
    workspace_id: workspaceId, name: workspaceId, path: "/test", created_at: "2026-09-30T04:00:00Z", lumon_version: "1.4.10", repositories: [],
    workflow_schedules: workspaceId === "workspace-one" ? [{ flow_id: flow.flow_id, name: flow.name, enabled: flow.schedule_enabled, schedule_expression: flow.schedule_expression }] : [],
  }));
  const flowRequest = vi.fn(async (path: string) => {
    if (path.endsWith("/flows")) return new Response(JSON.stringify([flow]));
    if (path === "/api/workspaces/workspace-one/flows/auto-guard") return new Response(JSON.stringify(flow));
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", flowRequest);
  const saveSchedule = vi.spyOn(dashboardApi, "updateFlowSchedule").mockImplementation(async (_workspaceId, _flowId, enabled, scheduleExpression) => {
    flow = { ...flow, schedule_enabled: enabled, schedule_expression: scheduleExpression };
    return flow;
  });
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><App /></I18nProvider>));
    const scheduled = Array.from(container.querySelectorAll<HTMLButtonElement>(".automation-summary")).find((row) => row.textContent?.includes("Auto Guard"))!;
    await act(async () => scheduled.click());
    expect(window.location.search).toContain("view=flows");
    expect(flowRequest).toHaveBeenCalledWith("/api/workspaces/workspace-one/flows/auto-guard", expect.any(Object));
    expect(container.querySelector(".flow-row.active strong")?.textContent).toBe("Auto Guard");
    expect(container.querySelector<HTMLInputElement>("#flow-schedule-expression")?.value).toBe("0 10 * * 1-5");
    expect(saveSchedule).not.toHaveBeenCalled();
    await act(async () => {
      const input = container.querySelector<HTMLInputElement>("#flow-schedule-expression")!;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "0 11 * * 1-5");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => container.querySelector<HTMLButtonElement>(".flow-schedule-panel .settings-actions button")!.click());
    expect(saveSchedule).toHaveBeenCalledWith("workspace-one", "auto-guard", true, "0 11 * * 1-5");
    await act(async () => container.querySelector<HTMLButtonElement>('.side-nav button[aria-label="Overview"]')!.click());
    expect(overview).toHaveBeenCalledTimes(2);
    expect(container.querySelector(".workspace-automation")?.textContent).toContain("0 11 * * 1-5");
    await act(async () => {
      const picker = container.querySelector<HTMLSelectElement>(".workspace-picker select")!;
      picker.value = "workspace-two";
      picker.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(container.querySelector(".workspace-automation")?.textContent).not.toContain("Auto Guard");
    await act(async () => container.querySelector<HTMLButtonElement>('.side-nav button[aria-label="Workflows"]')!.click());
    expect(container.querySelector("#flow-schedule-expression")).toBeNull();
    expect(flowRequest.mock.calls.filter(([path]) => path.endsWith("/auto-guard"))).toHaveLength(1);
  } finally {
    await act(async () => root.unmount());
  }
});
