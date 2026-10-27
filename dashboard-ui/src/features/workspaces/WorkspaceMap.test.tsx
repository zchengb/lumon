import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider, translate } from "../../shared/i18n";
import type { AgentSettings, CapabilitySummary, FlowSummary, WorkspaceOverview, WorkspaceSettings } from "../../shared/types";
import { WorkspaceMap } from "./WorkspaceMap";

const overview: WorkspaceOverview = {
  workspace_id: "one", name: "Example", path: "/example", created_at: "2026-10-22", lumon_version: "1.4.19",
  repositories: [], workflow_schedules: [{ flow_id: "review", name: "UI review", enabled: false, schedule_expression: "0 9 * * 1" }],
};
const capabilities: CapabilitySummary[] = [
  { capability_id: "db", name: "Read-only database", brief: "Read test data.", path: "lumon/capabilities/db.md", enabled: true, valid: true, error: null },
  { capability_id: "aws", name: "AWS", brief: "Inspect AWS.", path: "lumon/capabilities/aws.md", enabled: false, valid: true, error: null },
  { capability_id: "broken", name: "Broken capability", brief: "", path: "lumon/capabilities/broken.md", enabled: true, valid: false, error: "Invalid document" },
];
const flows: FlowSummary[] = [
  { flow_id: "review", name: "UI review", brief: "Capture screens.", path: "lumon/flows/review.md", enabled: true, valid: true, error: null },
  { flow_id: "paused", name: "Paused workflow", brief: "", path: "lumon/flows/paused.md", enabled: false, valid: true, error: null },
];
const settings: WorkspaceSettings = {
  workspace_id: "one", feishu_webhook: { enabled: false, configured: false, masked_url: null },
  auto_scan: { enabled: true, lookback_days: 7, trigger_hooks: [], schedule_expression: "0 12 * * 1-5", workflow_description: "" },
  auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" },
};
const agent: AgentSettings = {
  enabled: true, default_workspace_id: "other", agent_provider: "codex", agent_model: "example-model", agent_reasoning_effort: "high",
  feishu_app_id: "", feishu_app_configured: false, feishu_app_secret_masked: null,
  observability: { enabled: false, provider: "langfuse", base_url: "", sample_rate: 1, public_key_configured: false, secret_key_configured: false, public_key_masked: null, secret_key_masked: null },
};

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
  localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "listCapabilities").mockResolvedValue(capabilities);
  vi.spyOn(dashboardApi, "listFlows").mockResolvedValue(flows);
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

it.each(["en", "zh-CN", "zh-TW"] as const)("shows saved states and opens details before navigation (%s)", async (locale) => {
  localStorage.setItem("lumon.locale", locale);
  const container = document.createElement("div");
  const root = createRoot(container);
  const onNavigate = vi.fn();
  const onOpenWorkflow = vi.fn();
  const run = vi.spyOn(dashboardApi, "runFlow");
  const click = async (selector: string) => {
    const button = container.querySelector<HTMLButtonElement>(selector);
    expect(button).not.toBeNull();
    await act(async () => button!.click());
  };
  try {
    await act(async () => root.render(<I18nProvider><WorkspaceMap overview={overview} settings={settings} agentSettings={agent} onNavigate={onNavigate} onOpenWorkflow={onOpenWorkflow} /></I18nProvider>));
    expect(container.querySelector(".workspace-map-hub strong")?.textContent).toBe(overview.name);
    expect(container.querySelector(".workspace-map-hub small")?.textContent).toBe(`${overview.repositories.length} ${translate(locale, "overview.repositories")}`);
    expect(container.querySelector("h2")?.textContent).toBe(translate(locale, "map.title"));
    expect(container.querySelector(".workspace-map-count")?.textContent).toBe(translate(locale, "map.count", { enabled: 1, total: 3 }));
    const capabilityRows = container.querySelectorAll(".workspace-map-catalog li");
    expect(capabilityRows).toHaveLength(3);
    expect(capabilityRows[1].textContent).toContain(translate(locale, "settings.disabled"));
    expect(capabilityRows[2].textContent).toContain(translate(locale, "map.invalid"));
    expect(container.querySelector(".workspace-map-catalog")?.textContent).not.toContain(capabilities[0].brief);
    expect(container.querySelectorAll(".workspace-map-node")[1].textContent).toContain(translate(locale, "map.weekdaysAt", { time: "12:00" }));
    expect(container.querySelectorAll(".workspace-map-node")[2].textContent).toContain(translate(locale, "settings.disabled"));
    expect(container.querySelector(".workspace-map-flow-list small")?.textContent).toContain(translate(locale, "map.schedulePaused"));

    await click(".workspace-map-hub");
    expect(container.querySelector("dialog h3")?.textContent).toBe(overview.name);
    await click(".workspace-map-dialog-action");
    expect(onNavigate).toHaveBeenLastCalledWith("settings");
    for (const [index, view] of ["agent", "auto-scan", "auto-delivery"].entries()) {
      await click(`.workspace-map-node:nth-child(${index + 1})`);
      if (index === 0) expect(container.querySelector("dialog")?.textContent).toContain(translate(locale, "map.notDefault"));
      await click(".workspace-map-dialog-action");
      expect(onNavigate).toHaveBeenLastCalledWith(view);
    }
    await click(".workspace-map-context .workspace-map-panel-title button");
    expect(onNavigate).toHaveBeenLastCalledWith("capabilities");
    await click(".workspace-map-workflows .workspace-map-panel-title button");
    expect(onNavigate).toHaveBeenLastCalledWith("flows");
    await click(".workspace-map-catalog button");
    expect(container.querySelector("dialog p")?.textContent).toBe(capabilities[0].brief);
    await click(".workspace-map-dialog-action");
    expect(onNavigate).toHaveBeenLastCalledWith("capabilities");
    await click(".workspace-map-flow-list button");
    expect(container.querySelector("dialog p")?.textContent).toBe(flows[0].brief);
    await click(".workspace-map-dialog-action");
    expect(onOpenWorkflow).toHaveBeenCalledWith("review");
    const filters = container.querySelectorAll<HTMLButtonElement>(".workspace-map-filters button");
    await act(async () => filters[2].click());
    expect(filters[2].getAttribute("aria-pressed")).toBe("true");
    expect(container.querySelector(".workspace-map-body")?.getAttribute("data-focus")).toBe("workflows");
    expect(run).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it.each(["capability", "workflow"] as const)("keeps %s descriptions out of the map and renders them as plain text in details", async (catalog) => {
  const brief = "<img src=x onerror=alert(1)> **Not rendered as Markdown** " + "Long-description".repeat(30);
  if (catalog === "capability") {
    vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([{ ...capabilities[0], brief: `  ${brief}  ` }, { ...capabilities[1], brief: " \n " }]);
  } else {
    vi.mocked(dashboardApi.listFlows).mockResolvedValue([{ ...flows[0], brief: `  ${brief}  ` }, { ...flows[1], brief: " \n " }]);
  }
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><WorkspaceMap overview={overview} settings={settings} agentSettings={agent} onNavigate={vi.fn()} onOpenWorkflow={vi.fn()} /></I18nProvider>));
    const rows = container.querySelectorAll<HTMLButtonElement>(catalog === "capability" ? ".workspace-map-catalog button" : ".workspace-map-flow-list button");
    expect(container.textContent).not.toContain(brief);
    await act(async () => rows[0].click());
    const description = container.querySelector("dialog p");
    expect(description?.textContent).toBe(brief);
    expect(description?.querySelector("img")).toBeNull();
    expect(description?.querySelector("strong")).toBeNull();
    await act(async () => container.querySelector("dialog")!.dispatchEvent(new Event("cancel", { cancelable: true })));
    expect(container.querySelector("dialog")).toBeNull();
    await act(async () => rows[1].click());
    expect(container.querySelector("dialog p")?.textContent).toBe("No description provided");
  } finally { await act(async () => root.unmount()); }
});

it("renders recognized schedules in the local language and keeps other cron expressions intact", async () => {
  const container = document.createElement("div");
  const root = createRoot(container);
  const withSchedules = (delivery: string, scan: string) => ({ ...settings,
    auto_delivery: { ...settings.auto_delivery, schedule_expression: delivery },
    auto_scan: { ...settings.auto_scan, schedule_expression: scan },
  });
  const render = (delivery: string, scan: string) => <I18nProvider><WorkspaceMap overview={overview} settings={withSchedules(delivery, scan)} agentSettings={agent} onNavigate={vi.fn()} onOpenWorkflow={vi.fn()} /></I18nProvider>;
  try {
    await act(async () => root.render(render("*/5 * * * *", "0 10 * * 1-5")));
    expect(container.querySelectorAll(".workspace-map-node")[2].textContent).toContain("Every 5 minutes");
    expect(container.querySelectorAll(".workspace-map-node")[1].textContent).toContain("Weekdays · 10:00");
    await act(async () => root.render(render("*/1 * * * *", "*/7 * * * *")));
    expect(container.querySelectorAll(".workspace-map-node")[2].textContent).toContain("Every minute");
    expect(container.querySelectorAll(".workspace-map-node")[1].textContent).toContain("*/7 * * * *");
  } finally { await act(async () => root.unmount()); }
});

it("keeps one catalog usable when the other fails and never displays raw errors", async () => {
  vi.mocked(dashboardApi.listCapabilities).mockRejectedValue(new Error("secret response must not render"));
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><WorkspaceMap overview={overview} settings={null} agentSettings={null} onNavigate={vi.fn()} onOpenWorkflow={vi.fn()} /></I18nProvider>));
    expect(container.textContent).toContain("Catalog unavailable. Refresh to retry.");
    expect(container.textContent).toContain("UI review");
    expect(container.textContent).not.toContain("secret response");
    expect(container.querySelectorAll(".workspace-map-state")).toHaveLength(3);
    expect(Array.from(container.querySelectorAll(".workspace-map-state")).every((node) => node.textContent === "Unknown")).toBe(true);
  } finally { await act(async () => root.unmount()); }
});

it("shows empty catalogs instead of unavailable state", async () => {
  vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([]);
  vi.mocked(dashboardApi.listFlows).mockResolvedValue([]);
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><WorkspaceMap overview={overview} settings={settings} agentSettings={agent} onNavigate={vi.fn()} onOpenWorkflow={vi.fn()} /></I18nProvider>));
    expect(container.textContent).toContain("No capabilities registered yet.");
    expect(container.textContent).toContain("No workflows registered yet.");
    expect(container.textContent).not.toContain("Catalog unavailable");
  } finally { await act(async () => root.unmount()); }
});

it("discards old workspace responses, hides stale settings and reloads on refresh", async () => {
  let resolveOld: (value: CapabilitySummary[]) => void = () => {};
  vi.mocked(dashboardApi.listCapabilities).mockImplementation((id) => id === "one"
    ? new Promise((resolve) => { resolveOld = resolve; })
    : Promise.resolve([{ ...capabilities[0], name: "New workspace capability" }]));
  vi.mocked(dashboardApi.listFlows).mockResolvedValue([]);
  const container = document.createElement("div");
  const root = createRoot(container);
  const render = (data: WorkspaceOverview) => <I18nProvider><WorkspaceMap overview={data} settings={settings} agentSettings={null} onNavigate={vi.fn()} onOpenWorkflow={vi.fn()} /></I18nProvider>;
  try {
    await act(async () => root.render(render(overview)));
    expect(container.textContent).toContain("Reading catalog…");
    const next = { ...overview, workspace_id: "two", workflow_schedules: [] };
    await act(async () => root.render(render(next)));
    await act(async () => resolveOld(capabilities));
    expect(container.textContent).toContain("New workspace capability");
    expect(container.textContent).not.toContain("Read-only database");
    expect(container.textContent).not.toContain("0 12 * * 1-5");
    vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([]);
    await act(async () => root.render(render({ ...next })));
    expect(container.textContent).toContain("No capabilities registered yet.");
    expect(dashboardApi.listCapabilities).toHaveBeenLastCalledWith("two");
  } finally { await act(async () => root.unmount()); }
});

async function mountPollingMap() {
  vi.useFakeTimers();
  const container = document.createElement("div");
  const root = createRoot(container);
  await act(async () => root.render(<I18nProvider><WorkspaceMap overview={overview} settings={settings} agentSettings={agent} onNavigate={vi.fn()} onOpenWorkflow={vi.fn()} /></I18nProvider>));
  return { container, root };
}

it("refreshes an open detail and closes it if the catalog item is removed", async () => {
  const { container, root } = await mountPollingMap();
  try {
    await act(async () => container.querySelector<HTMLButtonElement>(".workspace-map-catalog button")!.click());
    expect(container.querySelector("dialog p")?.textContent).toBe("Read test data.");
    vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([{ ...capabilities[0], brief: "Updated guidance.", enabled: false }]);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(container.querySelector("dialog p")?.textContent).toBe("Updated guidance.");
    expect(container.querySelector("dialog")?.textContent).toContain("Disabled");
    vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([]);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(container.querySelector("dialog")).toBeNull();
  } finally { await act(async () => root.unmount()); }
});

it("polls changed capability and workflow catalogs without starting jobs", async () => {
  const run = vi.spyOn(dashboardApi, "runFlow");
  const { container, root } = await mountPollingMap();
  try {
    vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([{ ...capabilities[0], name: "New capability", enabled: false }]);
    vi.mocked(dashboardApi.listFlows).mockResolvedValue([{ ...flows[0], name: "New workflow", enabled: false }]);
    await act(async () => { await vi.advanceTimersByTimeAsync(14_999); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(2);
    expect(dashboardApi.listFlows).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("New capability");
    expect(container.textContent).toContain("New workflow");
    expect(container.textContent).toContain("0 / 1 enabled");
    expect(container.textContent).not.toContain("Read-only database");
    expect(container.textContent).not.toContain("Paused workflow");
    expect(run).not.toHaveBeenCalled();
  } finally { await act(async () => root.unmount()); }
});

it("pauses in hidden tabs, refreshes on return and removes polling on unmount", async () => {
  const { root } = await mountPollingMap();
  try {
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(1);
    expect(dashboardApi.listFlows).toHaveBeenCalledTimes(1);
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(2);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(3);
  } finally { await act(async () => root.unmount()); }
  expect(vi.getTimerCount()).toBe(0);
  await act(async () => {
    document.dispatchEvent(new Event("visibilitychange"));
    await vi.advanceTimersByTimeAsync(60_000);
  });
  expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(3);
});

it("does not fetch on a hidden initial mount", async () => {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  const { root } = await mountPollingMap();
  try {
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(dashboardApi.listCapabilities).not.toHaveBeenCalled();
    expect(dashboardApi.listFlows).not.toHaveBeenCalled();
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(1);
    expect(dashboardApi.listFlows).toHaveBeenCalledTimes(1);
  } finally { await act(async () => root.unmount()); }
});

it("never overlaps slow polls or clears the map while waiting", async () => {
  const { container, root } = await mountPollingMap();
  let resolvePoll: (value: CapabilitySummary[]) => void = () => {};
  try {
    vi.mocked(dashboardApi.listCapabilities).mockImplementationOnce(() => new Promise((resolve) => { resolvePoll = resolve; }));
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(2);
    expect(dashboardApi.listFlows).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("Read-only database");
    expect(container.textContent).not.toContain("Reading catalog…");
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      resolvePoll([]);
    });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("No capabilities registered yet.");
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(3);
  } finally { await act(async () => root.unmount()); }
});

it("retains failed catalog snapshots, then recovers automatically", async () => {
  const { container, root } = await mountPollingMap();
  try {
    vi.mocked(dashboardApi.listFlows).mockRejectedValueOnce(new Error("private failure"));
    vi.mocked(dashboardApi.listCapabilities).mockResolvedValue([]);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(container.textContent).toContain("UI review");
    expect(container.textContent).toContain("Catalog unavailable. Refresh to retry.");
    expect(container.textContent).toContain("No capabilities registered yet.");
    expect(container.textContent).not.toContain("private failure");
    vi.mocked(dashboardApi.listFlows).mockResolvedValue([]);
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    expect(container.textContent).toContain("No workflows registered yet.");
    expect(container.textContent).not.toContain("Catalog unavailable");
    expect(container.textContent).not.toContain("UI review");
  } finally { await act(async () => root.unmount()); }
});

it("ignores a poll that finishes after hiding the tab and refreshes on return", async () => {
  const { container, root } = await mountPollingMap();
  let resolvePoll: (value: CapabilitySummary[]) => void = () => {};
  try {
    vi.mocked(dashboardApi.listCapabilities).mockImplementationOnce(() => new Promise((resolve) => { resolvePoll = resolve; }));
    await act(async () => { await vi.advanceTimersByTimeAsync(15_000); });
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      resolvePoll([]);
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(container.textContent).toContain("Read-only database");
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(2);
    expect(vi.getTimerCount()).toBe(0);
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    await act(async () => { document.dispatchEvent(new Event("visibilitychange")); });
    expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(3);
  } finally { await act(async () => root.unmount()); }
});

it("does not reschedule a request that completes after leaving Overview", async () => {
  let resolveRequest: (value: CapabilitySummary[]) => void = () => {};
  vi.mocked(dashboardApi.listCapabilities).mockImplementationOnce(() => new Promise((resolve) => { resolveRequest = resolve; }));
  const { root } = await mountPollingMap();
  await act(async () => root.unmount());
  await act(async () => {
    resolveRequest(capabilities);
    await vi.advanceTimersByTimeAsync(60_000);
  });
  expect(vi.getTimerCount()).toBe(0);
  expect(dashboardApi.listCapabilities).toHaveBeenCalledTimes(1);
  expect(dashboardApi.listFlows).toHaveBeenCalledTimes(1);
});
