import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import { WorkspaceOnboarding } from "./WorkspaceOnboarding";

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

it("registers the searched MCP repository with its chosen scope", async () => {
  localStorage.setItem("lumon.locale", "en");
  const repository = { name: "app", full_name: "org/app", clone_url: "https://github.com/org/app.git", branch: "main", mcp_server: "github", auto_scan: true, auto_delivery: true };
  vi.spyOn(dashboardApi, "repositorySources").mockResolvedValue(["github.com"]);
  vi.spyOn(dashboardApi, "searchRepositories").mockResolvedValue([repository]);
  const initialize = vi.spyOn(dashboardApi, "initializeWorkspace").mockResolvedValue({ status: "initialized", workspace: "/workspace", workspace_id: "id" });
  const workspace = { workspace_id: "id", name: "Example", path: "/workspace", registered_at: "2026-10-28", health: "ready" as const, detail: "" };
  vi.spyOn(dashboardApi, "listWorkspaces").mockResolvedValue([workspace]);
  const ready = vi.fn();
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><WorkspaceOnboarding onReady={ready} onError={vi.fn()} /></I18nProvider>));
    const fill = async (id: string, value: string): Promise<void> => {
      const input = container.querySelector<HTMLInputElement>(id)!;
      await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value); input.dispatchEvent(new Event("input", { bubbles: true })); });
    };
    await fill("#workspace-path", "/workspace");
    await fill("#repository-search", "app");
    const search = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Search")!;
    await act(async () => search.click());
    await act(async () => container.querySelector<HTMLInputElement>('.repository-picker-results input')!.click());
    await act(async () => container.querySelector<HTMLInputElement>('input[aria-label="org/app Auto Scan"]')!.click());
    const submit = [...container.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent?.includes("Initialize workspace"))!;
    await act(async () => submit.click());
    expect(initialize).toHaveBeenCalledExactlyOnceWith({ path: "/workspace", repositories: [], remote_repositories: [{ ...repository, auto_scan: false }] });
    expect(ready).toHaveBeenCalledExactlyOnceWith(workspace);
  } finally { await act(async () => root.unmount()); }
});
