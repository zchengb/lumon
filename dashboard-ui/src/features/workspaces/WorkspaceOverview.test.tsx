import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { I18nProvider } from "../../shared/i18n";
import { WorkspaceOverview } from "./WorkspaceOverview";

afterEach(() => { localStorage.removeItem("lumon.locale"); });

it("shows saved automation configuration and navigates without starting jobs", async () => {
  localStorage.setItem("lumon.locale", "en");
  const container = document.createElement("div");
  const root = createRoot(container);
  const onNavigate = vi.fn();
  await act(async () => root.render(<I18nProvider><WorkspaceOverview
    overview={{ name: "Example", workspace_id: "workspace-id", path: "/example", created_at: "2026-09-29", lumon_version: "1.0.0", repositories: [] }}
    settings={{ workspace_id: "workspace-id", feishu_webhook: { enabled: false, configured: false, masked_url: null }, auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "" }, auto_scan: { enabled: true, trigger_hooks: [], schedule_expression: "0 12 * * 1-5", lookback_days: 7, workflow_description: "" } }}
    onRefresh={() => {}} refreshing={false} onNavigate={onNavigate}
  /></I18nProvider>));
  expect(container.textContent).toContain("0 12 * * 1-5");
  expect(container.textContent).toContain("No schedule configured");
  expect(container.textContent).toContain("Saved configuration");
  const shortcuts = container.querySelectorAll<HTMLButtonElement>(".workspace-shortcut-grid button");
  for (const [index, view] of ["agent", "flows", "capabilities", "auto-scan"].entries()) {
    await act(async () => shortcuts[index].click());
    expect(onNavigate).toHaveBeenLastCalledWith(view);
  }
  expect(container.querySelector(".automation-summary")?.textContent).toContain("Disabled");
  await act(async () => root.unmount());
});
