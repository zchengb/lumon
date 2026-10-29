import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { RemoteRepository, SetupReport } from "../../shared/types";
import { WorkspaceOnboarding } from "./WorkspaceOnboarding";

const repository: RemoteRepository = { name: "app", full_name: "org/app", clone_url: "https://github.com/org/app.git", branch: "main", mcp_server: "github", auto_scan: true, auto_delivery: true };
const report: SetupReport = { checks: ["git", "gh", "codex"].map((name) => ({ name, state: "ready", action: null, documentation_url: null })), hosts: ["github.com"], ready: true, agent_configured: false };
const workspace = { workspace_id: "id", name: "Example", path: "/workspace", registered_at: "2026-10-28", health: "ready" as const, detail: "" };

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "getSetup").mockResolvedValue(report);
  vi.spyOn(dashboardApi, "repositoryOrganizations").mockResolvedValue(["org"]);
  vi.spyOn(dashboardApi, "searchRepositories").mockResolvedValue([repository]);
  vi.spyOn(dashboardApi, "sourceRepositoryBranches").mockResolvedValue(["main", "release"]);
  vi.spyOn(dashboardApi, "initializeWorkspace").mockResolvedValue({ status: "initialized", workspace: "/workspace", workspace_id: "id" });
  vi.spyOn(dashboardApi, "listWorkspaces").mockResolvedValue([workspace]);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

async function mount() {
  const container = document.createElement("div");
  const root = createRoot(container);
  const ready = vi.fn(), error = vi.fn();
  await act(async () => root.render(<I18nProvider><WorkspaceOnboarding onReady={ready} onError={error} /></I18nProvider>));
  const button = (text: string) => [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.trim() === text)!;
  const click = async (selector: string) => act(async () => container.querySelector<HTMLElement>(selector)!.click());
  return { container, root, ready, error, button, click };
}

async function edit(input: HTMLInputElement, value: string) {
  await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value); input.dispatchEvent(new Event("input", { bubbles: true })); });
}

async function select(input: HTMLSelectElement, value: string) {
  await act(async () => { input.value = value; input.dispatchEvent(new Event("change", { bubbles: true })); });
}

it("lists repositories without a query and uses one table for selection, branch and scope", async () => {
  const ui = await mount();
  try {
    expect(dashboardApi.searchRepositories).toHaveBeenCalledExactlyOnceWith("github.com", "", 1);
    expect(ui.container.querySelectorAll("table")).toHaveLength(1);
    expect(ui.container.querySelector(".repository-picker-selected")).toBeNull();
    expect(ui.container.querySelector<HTMLInputElement>('[aria-label="org/app Auto Scan"]')!.disabled).toBe(true);
    await edit(ui.container.querySelector("#workspace-path")!, "/workspace");
    await ui.click('[aria-label="org/app"]');
    await ui.click('[aria-label="org/app Auto Scan"]');
    const branch = ui.container.querySelector<HTMLSelectElement>('[aria-label="org/app Target branch"]')!;
    await act(async () => branch.dispatchEvent(new Event("focusin", { bubbles: true })));
    await select(branch, "release");
    await act(async () => ui.button("Initialize workspace").click());
    expect(dashboardApi.initializeWorkspace).toHaveBeenCalledExactlyOnceWith({ path: "/workspace", repositories: [], remote_repositories: [{ ...repository, branch: "release", auto_scan: false }] });
    expect(ui.container.querySelector("h1")!.textContent).toBe("Workspace created");
    expect(ui.container.textContent).toContain("Agent is not configured");
    expect(ui.ready).not.toHaveBeenCalled();
    await act(async () => ui.button("Open settings").click());
    expect(ui.ready).toHaveBeenCalledExactlyOnceWith(workspace, "settings");
  } finally { await act(async () => ui.root.unmount()); }
});

it("offers overview only when dependencies and Agent configuration are ready", async () => {
  vi.mocked(dashboardApi.getSetup).mockResolvedValue({ ...report, agent_configured: true });
  const ui = await mount();
  try {
    await edit(ui.container.querySelector("#workspace-path")!, "/workspace");
    await ui.click('[aria-label="org/app"]');
    await act(async () => ui.button("Initialize workspace").click());
    await act(async () => ui.button("Open overview").click());
    expect(ui.ready).toHaveBeenCalledWith(workspace, "overview");
  } finally { await act(async () => ui.root.unmount()); }
});

it("shows loading before the check finishes and distinguishes missing tools", async () => {
  let finish!: (value: SetupReport) => void;
  vi.mocked(dashboardApi.getSetup).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  const ui = await mount();
  try {
    expect(ui.container.textContent).toContain("Checking dependencies");
    expect(ui.container.textContent).not.toContain("Sign in required");
    expect(ui.button("Initialize workspace").disabled).toBe(true);
    await act(async () => finish({ ...report, ready: false, hosts: [], checks: [{ name: "codex", state: "missing", action: "install codex", documentation_url: "https://developers.openai.com/codex/cli/" }, { name: "gh", state: "incompatible", action: "upgrade gh", documentation_url: "https://cli.github.com/" }] }));
    expect(ui.container.textContent).toContain("Not installed");
    expect(ui.container.textContent).toContain("Upgrade required");
    expect(ui.container.textContent).not.toContain("Sign in required");
    expect(ui.container.querySelectorAll(".setup-action code")).toHaveLength(2);
    expect(dashboardApi.searchRepositories).not.toHaveBeenCalled();
  } finally { await act(async () => ui.root.unmount()); }
});

it("does not call a check failure a missing login and can retry", async () => {
  vi.mocked(dashboardApi.getSetup).mockRejectedValueOnce(new Error("Check failed safely"));
  const ui = await mount();
  try {
    expect(ui.container.querySelector('[role="alert"]')!.textContent).toBe("Check failed safely");
    expect(ui.container.textContent).not.toContain("No GitHub CLI login");
    await act(async () => ui.button("Check again").click());
    expect(ui.container.querySelector("tbody")!.textContent).toContain("org/app");
  } finally { await act(async () => ui.root.unmount()); }
});

it("filters with an organization dropdown and retains selected repositories", async () => {
  const ui = await mount();
  try {
    await ui.click('[aria-label="org/app"]');
    vi.mocked(dashboardApi.searchRepositories).mockResolvedValue([]);
    await select(ui.container.querySelector("#repository-organization")!, "org");
    expect(dashboardApi.searchRepositories).toHaveBeenLastCalledWith("github.com", "", 1, "org");
    expect(ui.container.querySelector<HTMLInputElement>('[aria-label="org/app"]')!.checked).toBe(true);
    expect(ui.container.querySelectorAll("tbody tr")).toHaveLength(1);
  } finally { await act(async () => ui.root.unmount()); }
});

it("ignores a previous host response after switching sources", async () => {
  vi.mocked(dashboardApi.getSetup).mockResolvedValue({ ...report, hosts: ["one.ghe.com", "two.ghe.com"] });
  let finish!: (value: RemoteRepository[]) => void;
  vi.mocked(dashboardApi.searchRepositories).mockImplementation(async (host) => host === "one.ghe.com" ? new Promise((resolve) => { finish = resolve; }) : [{ ...repository, full_name: "org/new", name: "new", clone_url: "https://two.ghe.com/org/new.git" }]);
  const ui = await mount();
  try {
    await select(ui.container.querySelector("#repository-source")!, "two.ghe.com");
    await act(async () => finish([repository]));
    expect(ui.container.querySelector("tbody")!.textContent).toContain("org/new");
    expect(ui.container.querySelector("tbody")!.textContent).not.toContain("org/app");
  } finally { await act(async () => ui.root.unmount()); }
});

it("preserves selection and permits a retry after a later page fails", async () => {
  vi.mocked(dashboardApi.searchRepositories).mockResolvedValueOnce(Array.from({ length: 100 }, (_, index) => ({ ...repository, name: `app-${index}`, full_name: `org/app-${index}`, clone_url: `https://github.com/org/app-${index}.git` }))).mockRejectedValueOnce(new Error("Page failed")).mockResolvedValueOnce([repository]);
  const ui = await mount();
  try {
    await ui.click('[aria-label="org/app-0"]');
    await act(async () => ui.button("Load more").click());
    expect(ui.container.querySelectorAll("tbody tr")).toHaveLength(100);
    expect(ui.container.textContent).toContain("Page failed");
    await act(async () => ui.button("Load more").click());
    expect(ui.container.querySelectorAll("tbody tr")).toHaveLength(101);
    expect(ui.container.querySelector<HTMLInputElement>('[aria-label="org/app-0"]')!.checked).toBe(true);
  } finally { await act(async () => ui.root.unmount()); }
});

it("keeps the form after initialization fails and does not report completion", async () => {
  vi.mocked(dashboardApi.initializeWorkspace).mockRejectedValueOnce(new Error("Initialization rolled back"));
  const ui = await mount();
  try {
    await edit(ui.container.querySelector("#workspace-path")!, "/workspace");
    await ui.click('[aria-label="org/app"]');
    await act(async () => ui.button("Initialize workspace").click());
    expect(ui.error).toHaveBeenCalledWith("Initialization rolled back");
    expect(ui.container.querySelector<HTMLInputElement>('[aria-label="org/app"]')!.checked).toBe(true);
    expect(ui.ready).not.toHaveBeenCalled();
  } finally { await act(async () => ui.root.unmount()); }
});

it("loads later organization and branch pages without typing names", async () => {
  vi.mocked(dashboardApi.repositoryOrganizations).mockResolvedValueOnce(Array.from({ length: 100 }, (_, index) => `org-${index}`)).mockResolvedValueOnce(["last-org"]);
  vi.mocked(dashboardApi.sourceRepositoryBranches).mockResolvedValueOnce(Array.from({ length: 100 }, (_, index) => `branch-${index}`)).mockResolvedValueOnce(["last-branch"]);
  const ui = await mount();
  try {
    await select(ui.container.querySelector("#repository-organization")!, "__more__");
    expect(dashboardApi.repositoryOrganizations).toHaveBeenLastCalledWith("github.com", 2);
    expect(ui.container.querySelector("#repository-organization")!.textContent).toContain("last-org");
    expect(dashboardApi.searchRepositories).toHaveBeenCalledTimes(1);
    await ui.click('[aria-label="org/app"]');
    const branch = ui.container.querySelector<HTMLSelectElement>('[aria-label="org/app Target branch"]')!;
    await act(async () => branch.dispatchEvent(new Event("focusin", { bubbles: true })));
    await select(branch, "__more__");
    expect(dashboardApi.sourceRepositoryBranches).toHaveBeenLastCalledWith("github.com", "org/app", 2);
    await select(branch, "last-branch");
    expect(branch.value).toBe("last-branch");
  } finally { await act(async () => ui.root.unmount()); }
});

it("prevents duplicate initialization while a request is pending", async () => {
  let finish!: (value: { status: string; workspace: string; workspace_id: string }) => void;
  vi.mocked(dashboardApi.initializeWorkspace).mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  const ui = await mount();
  try {
    await edit(ui.container.querySelector("#workspace-path")!, "/workspace");
    await ui.click('[aria-label="org/app"]');
    const submit = ui.button("Initialize workspace");
    await act(async () => { submit.click(); submit.click(); });
    expect(dashboardApi.initializeWorkspace).toHaveBeenCalledTimes(1);
    expect(submit.disabled).toBe(true);
    await act(async () => finish({ status: "initialized", workspace: "/workspace", workspace_id: "id" }));
    expect(ui.container.querySelector("h1")!.textContent).toBe("Workspace created");
  } finally { await act(async () => ui.root.unmount()); }
});
