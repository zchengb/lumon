import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { I18nProvider } from "../shared/i18n";
import type { AgentSettings, SetupReport, WorkspaceListItem, WorkspaceSettings } from "../shared/types";
import { dashboardApi } from "./api";
import { App } from "./App";

vi.mock("../features/workspaces/WorkspaceOverview", () => ({
  WorkspaceOverview: ({ overview }: { overview: { name: string } }) => <h1>{overview.name}</h1>,
}));
vi.mock("../features/flows/FlowsPage", () => ({
  FlowsPage: ({ onDirtyChange }: { onDirtyChange: (dirty: boolean) => void }) => <input aria-label="Workflow draft" onChange={() => onDirtyChange(true)} />,
}));

const existing: WorkspaceListItem = { workspace_id: "existing", name: "Existing project", path: "/existing", registered_at: "2026-10-30", health: "ready", detail: "" };
const added: WorkspaceListItem = { ...existing, workspace_id: "new", name: "New project", path: "/new" };
const agent: AgentSettings = {
  enabled: true, default_workspace_id: "existing", agent_provider: "codex", agent_model: "test", agent_reasoning_effort: "high",
  feishu_app_id: "", feishu_app_configured: false, feishu_app_secret_masked: null,
  observability: { enabled: false, provider: "langfuse", base_url: "", sample_rate: 1, public_key_configured: false, secret_key_configured: false, public_key_masked: null, secret_key_masked: null },
};
const settings: WorkspaceSettings = {
  workspace_id: "existing", feishu_webhook: { enabled: false, configured: false, masked_url: null },
  auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" },
  auto_scan: { enabled: false, lookback_days: 7, trigger_hooks: [], schedule_expression: "", workflow_description: "" },
};
const setup: SetupReport = { checks: [], hosts: ["team.ghe.com", "github.com"], ready: true, agent_configured: true };
const repository = { name: "app", full_name: "org/app", clone_url: "https://github.com/org/app.git", branch: "main", mcp_server: "github", auto_scan: true, auto_delivery: true };
let registered: WorkspaceListItem[];

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  window.history.replaceState(null, "", "?workspace=existing&view=overview");
  registered = [existing];
  vi.spyOn(dashboardApi, "listWorkspaces").mockImplementation(async () => [...registered]);
  vi.spyOn(dashboardApi, "getBootstrap").mockResolvedValue({ version: "1.5.20", workspace_count: 1, has_workspaces: true });
  vi.spyOn(dashboardApi, "getAgentSettings").mockResolvedValue(agent);
  vi.spyOn(dashboardApi, "getSettings").mockImplementation(async (id) => ({ ...settings, workspace_id: id }));
  vi.spyOn(dashboardApi, "getOverview").mockImplementation(async (id) => ({ workspace_id: id, name: registered.find((item) => item.workspace_id === id)!.name, path: "/test", created_at: "2026-10-30", lumon_version: "1.5.20", repositories: [], workflow_schedules: [] }));
  vi.spyOn(dashboardApi, "getSetup").mockResolvedValue(setup);
  vi.spyOn(dashboardApi, "repositoryOrganizations").mockResolvedValue(["org"]);
  vi.spyOn(dashboardApi, "searchRepositories").mockImplementation(async (host) => [{ ...repository, clone_url: `https://${host}/org/app.git` }]);
  vi.spyOn(dashboardApi, "initializeWorkspace").mockImplementation(async () => {
    registered = [...registered, added];
    return { status: "initialized", workspace: added.path, workspace_id: added.workspace_id };
  });
  vi.spyOn(dashboardApi, "registerWorkspace").mockImplementation(async () => {
    registered = [...registered, added];
    return added;
  });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); window.history.replaceState(null, "", "/"); });

async function mount() {
  const container = document.createElement("div");
  const root = createRoot(container);
  await act(async () => root.render(<I18nProvider><App /></I18nProvider>));
  const button = (text: string) => [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.trim() === text)!;
  async function select(selector: string, value: string) {
    await act(async () => { const input = container.querySelector<HTMLSelectElement>(selector)!; input.value = value; input.dispatchEvent(new Event("change", { bubbles: true })); });
  }
  async function edit(selector: string, value: string) {
    await act(async () => { const input = container.querySelector<HTMLInputElement>(selector)!; Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value); input.dispatchEvent(new Event("input", { bubbles: true })); });
  }
  return { container, root, button, select, edit, add: () => select(".workspace-picker select", "__add_workspace__"), close: () => act(async () => root.unmount()) };
}

it.each([
  ["en", "Add workspace", "Cancel"], ["zh-CN", "新增工作区", "取消"], ["zh-TW", "新增工作區", "取消"],
])("opens and cancels adding another workspace in %s", async (locale, title, cancel) => {
  localStorage.setItem("lumon.locale", locale);
  const ui = await mount();
  try {
    expect(ui.container.querySelector(".workspace-picker select")!.lastElementChild?.textContent).toBe(`＋ ${title}`);
    await ui.add();
    expect(ui.container.querySelector("h1")?.textContent).toBe(title);
    expect(window.location.search).toContain("workspace=existing");
    await act(async () => ui.button(cancel).click());
    expect(ui.container.querySelector("h1")?.textContent).toBe(existing.name);
    expect(ui.container.querySelector<HTMLSelectElement>(".workspace-picker select")!.value).toBe(existing.workspace_id);
    expect(dashboardApi.initializeWorkspace).not.toHaveBeenCalled();
    expect(dashboardApi.registerWorkspace).not.toHaveBeenCalled();
  } finally { await ui.close(); }
});

it.each(["initialize", "register"])("adds a workspace through %s and selects it without losing the original", async (mode) => {
  const ui = await mount();
  try {
    await ui.add();
    await ui.edit("#workspace-path", added.path);
    if (mode === "initialize") {
      await ui.edit("#workspace-name", added.name);
      await ui.select("#repository-source", "github.com");
      await act(async () => ui.container.querySelector<HTMLInputElement>('[aria-label="org/app"]')!.click());
      await act(async () => ui.button("Initialize workspace").click());
      expect(dashboardApi.initializeWorkspace).toHaveBeenCalledExactlyOnceWith({ path: added.path, name: added.name, repositories: [], remote_repositories: [repository] });
      expect(dashboardApi.registerWorkspace).not.toHaveBeenCalled();
    } else {
      await act(async () => ui.button("Add existing").click());
      await act(async () => ui.button("Add workspace").click());
      expect(dashboardApi.registerWorkspace).toHaveBeenCalledExactlyOnceWith(added.path);
      expect(dashboardApi.initializeWorkspace).not.toHaveBeenCalled();
    }
    expect(ui.container.querySelector("h1")?.textContent).toBe("Workspace created");
    await act(async () => ui.button("Open overview").click());
    expect(ui.container.querySelector("h1")?.textContent).toBe(added.name);
    expect(window.location.search).toContain("workspace=new");
    const picker = ui.container.querySelector<HTMLSelectElement>(".workspace-picker select")!;
    expect(picker.value).toBe(added.workspace_id);
    expect([...picker.options].map((item) => item.value)).toEqual([existing.workspace_id, added.workspace_id, "__add_workspace__"]);
  } finally { await ui.close(); }
});

it("protects an unsaved draft before opening onboarding and returns to the original view", async () => {
  window.history.replaceState(null, "", "?workspace=existing&view=flows");
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const ui = await mount();
  try {
    await ui.edit('[aria-label="Workflow draft"]', "unsaved work");
    await ui.add();
    expect(confirm).toHaveBeenCalledOnce();
    expect(ui.container.querySelector<HTMLInputElement>('[aria-label="Workflow draft"]')!.value).toBe("unsaved work");
    expect(ui.container.querySelector<HTMLSelectElement>(".workspace-picker select")!.value).toBe(existing.workspace_id);
    confirm.mockReturnValue(true);
    await ui.add();
    await act(async () => ui.button("Cancel").click());
    expect(window.location.search).toContain("workspace=existing&view=flows");
    expect(ui.container.querySelector('[aria-label="Workflow draft"]')).not.toBeNull();
  } finally { await ui.close(); }
});

it("retains the form after failure and prevents cancellation or duplicate submission while creating", async () => {
  let finish!: (value: { status: string; workspace: string; workspace_id: string }) => void;
  vi.mocked(dashboardApi.initializeWorkspace).mockRejectedValueOnce(new Error("Creation failed")).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  const ui = await mount();
  try {
    await ui.add();
    await ui.edit("#workspace-path", added.path);
    await act(async () => ui.container.querySelector<HTMLInputElement>('[aria-label="org/app"]')!.click());
    await act(async () => ui.button("Initialize workspace").click());
    expect(ui.container.textContent).toContain("Creation failed");
    expect(ui.container.querySelector<HTMLInputElement>("#workspace-path")!.value).toBe(added.path);
    expect(ui.container.querySelector<HTMLInputElement>('[aria-label="org/app"]')!.checked).toBe(true);
    expect(ui.button("Cancel").disabled).toBe(false);
    await act(async () => ui.button("Initialize workspace").click());
    expect(ui.button("Cancel").disabled).toBe(true);
    await act(async () => ui.button("Cancel").click());
    expect(ui.container.querySelector("h1")?.textContent).toBe("Add workspace");
    expect(dashboardApi.initializeWorkspace).toHaveBeenCalledTimes(2);
    registered = [...registered, added];
    await act(async () => finish({ status: "initialized", workspace: added.path, workspace_id: added.workspace_id }));
    await act(async () => ui.button("Open overview").click());
    expect(ui.container.querySelector("h1")?.textContent).toBe(added.name);
  } finally { await ui.close(); }
});

it("keeps first-time onboarding without a cancel action", async () => {
  registered = [];
  const ui = await mount();
  try {
    expect(ui.container.querySelector("h1")?.textContent).toBe("Connect a workspace first");
    expect(ui.button("Cancel")).toBeUndefined();
  } finally { await ui.close(); }
});
