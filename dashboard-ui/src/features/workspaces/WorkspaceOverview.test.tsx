import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { I18nProvider, translate } from "../../shared/i18n";
import { WorkspaceOverview } from "./WorkspaceOverview";

afterEach(() => { localStorage.removeItem("lumon.locale"); });

it("shows saved automation configuration and navigates without starting jobs", async () => {
  localStorage.setItem("lumon.locale", "en");
  const container = document.createElement("div");
  const root = createRoot(container);
  const onNavigate = vi.fn();
  await act(async () => root.render(<I18nProvider><WorkspaceOverview
    overview={{ name: "Example", workspace_id: "workspace-id", path: "/example", created_at: "2026-09-29", lumon_version: "1.0.0", repositories: [], workflow_schedules: [] }}
    settings={{ workspace_id: "workspace-id", feishu_webhook: { enabled: false, configured: false, masked_url: null }, auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" }, auto_scan: { enabled: true, trigger_hooks: [], schedule_expression: "0 12 * * 1-5", lookback_days: 7, workflow_description: "" } }}
    onRefresh={() => {}} refreshing={false} onNavigate={onNavigate} onOpenWorkflow={vi.fn()}
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

it.each(["en", "zh-CN", "zh-TW"] as const)("shows saved workflow schedules and opens the matching workflow (%s)", async (locale) => {
  localStorage.setItem("lumon.locale", locale);
  const container = document.createElement("div");
  const root = createRoot(container);
  const onOpenWorkflow = vi.fn();
  try {
    await act(async () => root.render(<I18nProvider><WorkspaceOverview
      overview={{ name: "Example", workspace_id: "workspace-id", path: "/example", created_at: "2026-09-29", lumon_version: "1.0.0", repositories: [], workflow_schedules: [
        { flow_id: "auto-guard", name: "Auto Guard", enabled: true, schedule_expression: "0 10 * * 1-5" },
        { flow_id: "weekly-review", name: "Weekly review", enabled: false, schedule_expression: "0 9 * * 1" },
      ] }}
      settings={null} onRefresh={() => {}} refreshing={false} onNavigate={vi.fn()} onOpenWorkflow={onOpenWorkflow}
    /></I18nProvider>));
    const rows = container.querySelectorAll<HTMLButtonElement>(".automation-summary");
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain("Auto Guard");
    expect(rows[0].querySelector(".health-ok")?.textContent).toBe(translate(locale, "settings.enabled"));
    expect(rows[0].querySelector("code")?.textContent).toBe("0 10 * * 1-5");
    expect(rows[1].querySelector("small")?.textContent).toBe(translate(locale, "settings.disabled"));
    await act(async () => rows[0].click());
    expect(onOpenWorkflow).toHaveBeenLastCalledWith("auto-guard");
    await act(async () => rows[1].click());
    expect(onOpenWorkflow).toHaveBeenLastCalledWith("weekly-review");
  } finally {
    await act(async () => root.unmount());
  }
});
