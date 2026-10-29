import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { RemoteRepository, WorkspaceOverview } from "../../shared/types";
import { RepositoriesPage } from "./RepositoriesPage";

const repository: RemoteRepository = { name: "app", full_name: "org/app", clone_url: "https://github.com/org/app.git", branch: "main", mcp_server: "github", auto_scan: true, auto_delivery: true };
const overview: WorkspaceOverview = {
  workspace_id: "workspace", name: "Example", path: "/workspace", created_at: "2026-10-28",
  lumon_version: "1.0", repositories_version: "abc", workflow_schedules: [],
  repositories: [{ name: "app", path: "/workspace/repos/app", branch: "release", health: "ready", detail: "", auto_scan: false, auto_delivery: true }],
};

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "repositorySources").mockResolvedValue(["github.com"]);
  vi.spyOn(dashboardApi, "searchRepositories").mockResolvedValue([repository]);
  vi.spyOn(dashboardApi, "updateRepositoryScopes").mockResolvedValue({ repositories_version: "version-2" });
  vi.spyOn(dashboardApi, "repositoryBranches").mockResolvedValue(["main", "release", "release/next"]);
  vi.spyOn(dashboardApi, "updateRepositoryBranch").mockResolvedValue({ repositories_version: "branch-version" });
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); document.body.innerHTML = ""; });

async function mount(data = overview) {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  const onRefresh = vi.fn().mockResolvedValue(undefined);
  const onDirtyChange = vi.fn();
  await act(async () => root.render(<I18nProvider><RepositoriesPage overview={data} onRefresh={onRefresh} onDirtyChange={onDirtyChange} onNotice={vi.fn()} /></I18nProvider>));
  const button = (label: string) => [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === label)!;
  return { container, root, button, onRefresh, onDirtyChange };
}

async function edit(field: HTMLInputElement, text: string): Promise<void> {
  await act(async () => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(field, text);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function selectBranch(select: HTMLSelectElement, branch: string): Promise<void> {
  await act(async () => { select.value = branch; select.dispatchEvent(new Event("change", { bubbles: true })); });
}

it("loads branches on demand and saves a selection before the next scope change", async () => {
  const { container, root, onRefresh, onDirtyChange } = await mount();
  try {
    const branch = container.querySelector<HTMLSelectElement>('select[aria-label="app Target branch"]')!;
    expect(branch.value).toBe("release");
    expect(dashboardApi.repositoryBranches).not.toHaveBeenCalled();
    await act(async () => branch.focus());
    expect(dashboardApi.repositoryBranches).toHaveBeenCalledExactlyOnceWith("workspace", "app");
    expect([...branch.options].map((item) => item.value)).toEqual(["release", "main", "release/next"]);
    await selectBranch(branch, "release/next");
    expect(dashboardApi.updateRepositoryBranch).toHaveBeenCalledExactlyOnceWith("workspace", "app", "abc", "release/next");
    expect(onRefresh).toHaveBeenCalledOnce();
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
    await act(async () => container.querySelector<HTMLInputElement>('input[aria-label="app Auto Scan"]')!.click());
    expect(dashboardApi.updateRepositoryScopes).toHaveBeenLastCalledWith("workspace", "branch-version", [{ name: "app", auto_scan: true, auto_delivery: true }]);
  } finally { await act(async () => root.unmount()); }
});

it("blocks conflicting edits during a branch save and restores a failed selection", async () => {
  let rejectSave!: (reason: Error) => void;
  vi.mocked(dashboardApi.updateRepositoryBranch).mockReturnValue(new Promise((_resolve, reject) => { rejectSave = reject; }));
  const { container, root, onDirtyChange } = await mount();
  try {
    const branch = container.querySelector<HTMLSelectElement>('select[aria-label="app Target branch"]')!;
    await act(async () => branch.focus());
    await selectBranch(branch, "main");
    expect(branch.disabled).toBe(true);
    expect(container.querySelector<HTMLInputElement>('input[role="switch"]')!.disabled).toBe(true);
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    await act(async () => rejectSave(new Error("Target branch no longer exists")));
    expect(branch.value).toBe("release");
    expect(branch.disabled).toBe(false);
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Target branch no longer exists");
    await act(async () => branch.dispatchEvent(new Event("pointerdown", { bubbles: true })));
    expect(dashboardApi.repositoryBranches).toHaveBeenCalledTimes(2);
  } finally { await act(async () => root.unmount()); }
});

it("can retry loading branches and preserves a confirmed branch if refreshing fails", async () => {
  vi.mocked(dashboardApi.repositoryBranches).mockRejectedValueOnce(new Error("Connection failed"));
  const { container, root, button, onRefresh } = await mount();
  const add = vi.spyOn(dashboardApi, "addRepositories").mockResolvedValue();
  try {
    const branch = container.querySelector<HTMLSelectElement>('select[aria-label="app Target branch"]')!;
    await act(async () => branch.focus());
    expect(branch.value).toBe("release");
    expect(container.querySelector('[role="alert"]')?.textContent).toBe("Connection failed");
    await act(async () => branch.dispatchEvent(new Event("pointerdown", { bubbles: true })));
    onRefresh.mockRejectedValueOnce(new Error("Refresh failed"));
    await selectBranch(branch, "main");
    expect(branch.value).toBe("main");
    await act(async () => button("GitHub MCP").click());
    await act(async () => button("Connect").click());
    expect(add).toHaveBeenLastCalledWith("workspace", "branch-version", [{ ...repository, branch: "main", auto_scan: false }]);
  } finally { await act(async () => root.unmount()); }
});

it("loads all repositories on entry and keeps the existing branch when connecting", async () => {
  const add = vi.spyOn(dashboardApi, "addRepositories").mockResolvedValue();
  const { container, root, button, onRefresh } = await mount();
  try {
    expect(dashboardApi.searchRepositories).toHaveBeenCalledExactlyOnceWith("github.com", "", 1);
    expect(container.querySelector("details")).toBeNull();
    expect(container.querySelector('input[role="switch"][aria-label="app Auto Scan"]')).not.toBeNull();
    await act(async () => button("GitHub MCP").click());
    expect(container.querySelector('input[aria-label="org/app Target branch"]')).toBeNull();
    expect(container.querySelector("tbody")?.textContent).toContain("release");
    await act(async () => button("Connect").click());
    expect(add).toHaveBeenCalledExactlyOnceWith("workspace", "abc", [{ ...repository, branch: "release", auto_scan: false }]);
    expect(onRefresh).toHaveBeenCalledOnce();
  } finally { await act(async () => root.unmount()); }
});

it("saves each toggle immediately and restores its previous value on failure", async () => {
  const save = vi.spyOn(dashboardApi, "updateRepositoryScopes").mockRejectedValue(new Error("Settings changed. Refresh and try again."));
  const { container, root, button, onRefresh, onDirtyChange } = await mount();
  try {
    const scan = container.querySelector<HTMLInputElement>('input[aria-label="app Auto Scan"]')!;
    expect(button("Save scope")).toBeUndefined();
    await act(async () => scan.click());
    expect(save).toHaveBeenCalledExactlyOnceWith("workspace", "abc", [{ name: "app", auto_scan: true, auto_delivery: true }]);
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Settings changed");
    expect(scan.checked).toBe(false);
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
    expect(onRefresh).not.toHaveBeenCalled();
    save.mockResolvedValue({ repositories_version: "version-2" });
    await act(async () => scan.click());
    expect(onRefresh).toHaveBeenCalledOnce();
    expect(scan.checked).toBe(true);
    expect(container.querySelector('[role="alert"]')).toBeNull();
  } finally { await act(async () => root.unmount()); }
});

it("searches and restores the complete list when the search is cleared", async () => {
  const { container, root, button } = await mount();
  try {
    await act(async () => button("GitHub MCP").click());
    const query = container.querySelector<HTMLInputElement>('input[aria-label="Search repositories"]')!;
    await edit(query, "backend");
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(dashboardApi.searchRepositories).toHaveBeenLastCalledWith("github.com", "backend", 1);
    await edit(query, "");
    await act(async () => container.querySelector("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(dashboardApi.searchRepositories).toHaveBeenLastCalledWith("github.com", "", 1);
  } finally { await act(async () => root.unmount()); }
});

it("loads the next page and preserves the list after a page failure", async () => {
  const firstPage = Array.from({ length: 100 }, (_, index) => ({ ...repository, name: `app-${index}`, full_name: `org/app-${index}`, clone_url: `https://github.com/org/app-${index}.git` }));
  vi.mocked(dashboardApi.searchRepositories).mockResolvedValueOnce(firstPage).mockRejectedValueOnce(new Error("GitHub is unavailable")).mockResolvedValueOnce([repository]);
  const { container, root, button } = await mount();
  try {
    await act(async () => button("GitHub MCP").click());
    await act(async () => button("Load more").click());
    expect(container.querySelectorAll("tbody tr")).toHaveLength(100);
    expect(container.querySelector('[role="alert"]')?.textContent).toBe("GitHub is unavailable");
    await act(async () => button("Load more").click());
    expect(dashboardApi.searchRepositories).toHaveBeenLastCalledWith("github.com", "", 2);
    expect(container.querySelectorAll("tbody tr")).toHaveLength(101);
    expect(button("Load more")).toBeUndefined();
  } finally { await act(async () => root.unmount()); }
});

it("ignores results from an old source after the source changes", async () => {
  vi.mocked(dashboardApi.repositorySources).mockResolvedValue(["github.com", "team.ghe.com"]);
  let finishFirst!: (repositories: RemoteRepository[]) => void;
  vi.mocked(dashboardApi.searchRepositories).mockReturnValueOnce(new Promise((resolve) => { finishFirst = resolve; })).mockResolvedValueOnce([{ ...repository, full_name: "team/service" }]);
  const { container, root, button } = await mount();
  try {
    await act(async () => button("GitHub MCP").click());
    const source = container.querySelector<HTMLSelectElement>('select[aria-label="GitHub MCP source"]')!;
    await act(async () => { source.value = "team.ghe.com"; source.dispatchEvent(new Event("change", { bubbles: true })); });
    await act(async () => finishFirst([repository]));
    expect(container.querySelector("tbody")?.textContent).toContain("team/service");
    expect(container.querySelector("tbody")?.textContent).not.toContain("org/app");
  } finally { await act(async () => root.unmount()); }
});

it("shows repositories that are already connected", async () => {
  const { container, root, button } = await mount({ ...overview, repositories: [{ ...overview.repositories[0], mcp_server: "github", remote_name: "org/app" }] });
  try {
    await act(async () => button("GitHub MCP").click());
    expect(container.querySelector("tbody")?.textContent).toContain("Connected");
    expect(container.querySelector('[aria-label="Connect org/app"]')).toBeNull();
  } finally { await act(async () => root.unmount()); }
});

it("waits for a pending save before connecting and preserves the saved scope", async () => {
  let finishSave!: (response: { repositories_version: string }) => void;
  vi.mocked(dashboardApi.updateRepositoryScopes).mockReturnValue(new Promise((resolve) => { finishSave = resolve; }));
  const add = vi.spyOn(dashboardApi, "addRepositories").mockResolvedValue();
  const { container, root, button } = await mount();
  try {
    await act(async () => container.querySelector<HTMLInputElement>('input[aria-label="app Auto Scan"]')!.click());
    await act(async () => button("GitHub MCP").click());
    expect(button("Connect").disabled).toBe(true);
    await act(async () => finishSave({ repositories_version: "version-2" }));
    await act(async () => button("Connect").click());
    expect(add).toHaveBeenCalledExactlyOnceWith("workspace", "version-2", [{ ...repository, branch: "release", auto_scan: true }]);
  } finally { await act(async () => root.unmount()); }
});

it("serializes saves and uses the returned version for the next toggle", async () => {
  let finishSave!: (response: { repositories_version: string }) => void;
  const save = vi.mocked(dashboardApi.updateRepositoryScopes).mockReturnValueOnce(new Promise((resolve) => { finishSave = resolve; }));
  const { container, root, onDirtyChange } = await mount();
  try {
    const scan = container.querySelector<HTMLInputElement>('input[aria-label="app Auto Scan"]')!;
    const delivery = container.querySelector<HTMLInputElement>('input[aria-label="app Auto Delivery"]')!;
    await act(async () => scan.click());
    expect(scan.checked).toBe(true);
    expect(scan.disabled).toBe(true);
    expect(delivery.disabled).toBe(true);
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    await act(async () => delivery.click());
    expect(save).toHaveBeenCalledTimes(1);
    await act(async () => finishSave({ repositories_version: "version-2" }));
    expect(delivery.disabled).toBe(false);
    await act(async () => delivery.click());
    expect(save).toHaveBeenLastCalledWith("workspace", "version-2", [{ name: "app", auto_scan: true, auto_delivery: false }]);
    expect(scan.checked).toBe(true);
    expect(delivery.checked).toBe(false);
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally { await act(async () => root.unmount()); }
});

it("keeps a confirmed save if the follow-up refresh fails", async () => {
  const { container, root, onRefresh } = await mount();
  onRefresh.mockRejectedValueOnce(new Error("Unable to refresh"));
  try {
    const scan = container.querySelector<HTMLInputElement>('input[aria-label="app Auto Scan"]')!;
    const delivery = container.querySelector<HTMLInputElement>('input[aria-label="app Auto Delivery"]')!;
    await act(async () => scan.click());
    expect(scan.checked).toBe(true);
    expect(container.querySelector('[role="alert"]')?.textContent).toBe("Unable to refresh");
    await act(async () => delivery.click());
    expect(dashboardApi.updateRepositoryScopes).toHaveBeenLastCalledWith("workspace", "version-2", [{ name: "app", auto_scan: true, auto_delivery: false }]);
  } finally { await act(async () => root.unmount()); }
});

it("uses the current configured branch when a catalog response arrives after a refresh", async () => {
  let finishSearch!: (repositories: RemoteRepository[]) => void;
  vi.mocked(dashboardApi.searchRepositories).mockReturnValue(new Promise((resolve) => { finishSearch = resolve; }));
  const add = vi.spyOn(dashboardApi, "addRepositories").mockResolvedValue();
  const { container, root, button, onRefresh, onDirtyChange } = await mount();
  try {
    await act(async () => root.render(<I18nProvider><RepositoriesPage overview={{ ...overview, repositories_version: "new-version", repositories: [{ ...overview.repositories[0], branch: "current-release" }] }} onRefresh={onRefresh} onDirtyChange={onDirtyChange} onNotice={vi.fn()} /></I18nProvider>));
    await act(async () => finishSearch([repository]));
    await act(async () => button("GitHub MCP").click());
    expect(container.querySelector("tbody")?.textContent).toContain("current-release");
    await act(async () => button("Connect").click());
    expect(add).toHaveBeenCalledExactlyOnceWith("workspace", "new-version", [{ ...repository, branch: "current-release", auto_scan: false }]);
  } finally { await act(async () => root.unmount()); }
});

it("moves keyboard focus between tabs with arrows and Home", async () => {
  const { container, root } = await mount();
  try {
    const workspace = container.querySelector<HTMLButtonElement>("#workspace-repositories-tab")!;
    const github = container.querySelector<HTMLButtonElement>("#github-repositories-tab")!;
    expect(workspace.tabIndex).toBe(0);
    expect(github.tabIndex).toBe(-1);
    await act(async () => workspace.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true })));
    expect(github.tabIndex).toBe(0);
    expect(workspace.tabIndex).toBe(-1);
    expect(document.activeElement).toBe(github);
    await act(async () => github.dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true })));
    expect(document.activeElement).toBe(workspace);
    expect(workspace.getAttribute("aria-selected")).toBe("true");
  } finally { await act(async () => root.unmount()); }
});
