import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { WorkspaceOverview } from "../../shared/types";
import { RepositoryManager } from "./RepositoryManager";

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

it("saves the selected automation scope without changing the repository", async () => {
  localStorage.setItem("lumon.locale", "en");
  const overview: WorkspaceOverview = {
    workspace_id: "workspace", name: "Example", path: "/workspace", created_at: "2026-10-28",
    lumon_version: "1.0", repositories_version: "abc", workflow_schedules: [],
    repositories: [{ name: "app", path: "/workspace/repos/app", branch: "main", health: "ready", detail: "", auto_scan: true, auto_delivery: true }],
  };
  vi.spyOn(dashboardApi, "repositorySources").mockResolvedValue(["github.com"]);
  const save = vi.spyOn(dashboardApi, "updateRepositoryScopes").mockResolvedValue();
  const refresh = vi.fn();
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><RepositoryManager overview={overview} onRefresh={refresh} /></I18nProvider>));
    const details = container.querySelector("details")!;
    await act(async () => { details.open = true; details.dispatchEvent(new Event("toggle")); });
    const scan = container.querySelector<HTMLInputElement>('input[aria-label="app Auto Scan"]')!;
    await act(async () => scan.click());
    const button = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Save scope")!;
    await act(async () => button.click());
    expect(save).toHaveBeenCalledExactlyOnceWith("workspace", "abc", [{ name: "app", auto_scan: false, auto_delivery: true }]);
    expect(refresh).toHaveBeenCalledOnce();
  } finally { await act(async () => root.unmount()); }
});

it("keeps an existing branch when connecting the repository to MCP", async () => {
  localStorage.setItem("lumon.locale", "en");
  const overview: WorkspaceOverview = {
    workspace_id: "workspace", name: "Example", path: "/workspace", created_at: "2026-10-28",
    lumon_version: "1.0", repositories_version: "abc", workflow_schedules: [],
    repositories: [{ name: "app", path: "/workspace/repos/app", branch: "release", health: "ready", detail: "", auto_scan: false, auto_delivery: true }],
  };
  const repository = { name: "app", full_name: "org/app", clone_url: "https://github.com/org/app.git", branch: "main", mcp_server: "github", auto_scan: true, auto_delivery: true };
  vi.spyOn(dashboardApi, "repositorySources").mockResolvedValue(["github.com"]);
  vi.spyOn(dashboardApi, "searchRepositories").mockResolvedValue([repository]);
  const add = vi.spyOn(dashboardApi, "addRepositories").mockResolvedValue();
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><RepositoryManager overview={overview} onRefresh={vi.fn()} /></I18nProvider>));
    const details = container.querySelector("details")!;
    await act(async () => { details.open = true; details.dispatchEvent(new Event("toggle")); });
    const query = container.querySelector<HTMLInputElement>("#manage-query")!;
    await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(query, "app"); query.dispatchEvent(new Event("input", { bubbles: true })); });
    const search = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Search")!;
    await act(async () => search.click());
    expect(container.querySelector<HTMLInputElement>('input[aria-label="org/app Target branch"]')!.value).toBe("release");
    const connect = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Connect")!;
    await act(async () => connect.click());
    expect(add).toHaveBeenCalledExactlyOnceWith("workspace", "abc", [{ ...repository, branch: "release", auto_scan: false }]);
  } finally { await act(async () => root.unmount()); }
});
