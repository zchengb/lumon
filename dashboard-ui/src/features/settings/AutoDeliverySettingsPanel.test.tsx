import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "../../shared/i18n";
import type { WorkspaceSettings } from "../../shared/types";
import { AutoDeliverySettingsPanel } from "./AutoDeliverySettingsPanel";

it.each(["en", "zh-CN", "zh-TW"] as const)("saves a multiline trigger prompt and supports clearing it while disabled in %s", async (locale) => {
  const settings: WorkspaceSettings = {
    workspace_id: "workspace-id",
    feishu_webhook: { enabled: true, configured: true, masked_url: null },
    auto_delivery: { enabled: false, trigger_hooks: ["jira.delivery_ready", "mail.delivery_ready"], schedule_expression: "*/5 * * * *", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" },
    auto_scan: { enabled: false, trigger_hooks: [], schedule_expression: "0 12 * * 1-5", lookback_days: 7, workflow_description: "Review confirmed bugs only." },
  };
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onSave = vi.fn().mockResolvedValue(true);
  const onDirtyChange = vi.fn();
  const prompt = "Check approved Stories.\n\n1. Verify the requirements.\n2. Follow the delivery workflow.";
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", locale);
    const render = async (next: WorkspaceSettings) => act(async () => root.render(<I18nProvider><AutoDeliverySettingsPanel
      settings={next} onSave={onSave} onDirtyChange={onDirtyChange}
    /></I18nProvider>));
    await render(settings);
    const field = container.querySelector<HTMLTextAreaElement>("#auto-delivery-hooks")!;
    const save = container.querySelector<HTMLButtonElement>(".settings-actions button")!;
    expect(field.value).toBe("jira.delivery_ready\nmail.delivery_ready");
    expect(field.maxLength).toBe(8000);
    expect(field.getAttribute("aria-describedby")).toBeNull();
    expect(container.querySelector("#auto-delivery-hooks-help")).toBeNull();
    expect(field.classList.contains("mono")).toBe(false);
    expect(field.placeholder).not.toBe("jira.delivery_ready");
    expect(save.disabled).toBe(true);
    expect(save.textContent).toBe({ en: "Save", "zh-CN": "保存", "zh-TW": "儲存" }[locale]);

    const fill = async (text: string) => act(async () => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(field, text);
      field.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await fill(prompt);
    await act(async () => save.click());
    expect(onSave).toHaveBeenLastCalledWith({
      feishu_webhook: { enabled: true },
      auto_delivery: { ...settings.auto_delivery, trigger_hooks: [prompt] },
    });
    await render({ ...settings, auto_delivery: { ...settings.auto_delivery, trigger_hooks: [prompt] } });
    expect(field.value).toBe(prompt);
    expect(save.disabled).toBe(true);

    await fill(" \n ");
    await act(async () => save.click());
    expect(onSave).toHaveBeenLastCalledWith({
      feishu_webhook: { enabled: true },
      auto_delivery: { ...settings.auto_delivery, trigger_hooks: [] },
    });
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally {
    await act(async () => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.removeItem("lumon.locale");
  }
});

it("keeps Jira detection and publication edits scoped to this panel, including a failed save", async () => {
  const settings: WorkspaceSettings = {
    workspace_id: "workspace-id",
    feishu_webhook: { enabled: false, configured: false, masked_url: null },
    auto_delivery: { enabled: false, trigger_hooks: ["Deliver flagged Stories."], schedule_expression: "*/5 * * * *", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" },
    auto_scan: { enabled: false, trigger_hooks: [], schedule_expression: "0 12 * * 1-5", lookback_days: 7, workflow_description: "Review bugs only." },
  };
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onSave = vi.fn().mockResolvedValue(false);
  const onDirtyChange = vi.fn();
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", "en");
    await act(async () => root.render(<I18nProvider><AutoDeliverySettingsPanel
      settings={settings} onSave={onSave} onDirtyChange={onDirtyChange}
    /></I18nProvider>));
    const policy = container.querySelector<HTMLSelectElement>("#auto-delivery-publish-mode")!;
    const save = container.querySelector<HTMLButtonElement>(".settings-actions button")!;
    const toggle = container.querySelector<HTMLInputElement>('[role="switch"]')!;
    expect(policy.value).toBe("local");
    expect(Array.from(policy.options, (option) => option.value)).toEqual(["local", "branch", "pr", "direct"]);
    expect(container.querySelector("#auto-delivery-target-branch")).toBeNull();
    await act(async () => toggle.click());
    expect(save.disabled).toBe(true);
    expect(container.querySelector('[role="status"]')?.textContent).toContain("before enabling");
    await act(async () => toggle.click());
    await act(async () => { policy.value = "pr"; policy.dispatchEvent(new Event("change", { bubbles: true })); });
    const fill = async (id: string, text: string) => act(async () => {
      const field = container.querySelector<HTMLInputElement | HTMLTextAreaElement>(id)!;
      const prototype = field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(field, text);
      field.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await fill("#auto-delivery-jira-site", "test.atlassian.net");
    await fill("#auto-delivery-jql", "project = TEST AND Flagged = Impediment");
    await fill("#auto-delivery-target-branch", "release");
    await act(async () => save.click());
    expect(onSave).toHaveBeenLastCalledWith({
      feishu_webhook: { enabled: false },
      auto_delivery: { ...settings.auto_delivery, jira_site: "test.atlassian.net", trigger_jql: "project = TEST AND Flagged = Impediment", publish_mode: "pr", target_branch: "release" },
    });
    expect(save.disabled).toBe(false);
    expect(container.querySelector<HTMLInputElement>("#auto-delivery-target-branch")!.value).toBe("release");
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    expect(onSave.mock.calls[0][0]).not.toHaveProperty("auto_scan");
  } finally {
    await act(async () => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.removeItem("lumon.locale");
  }
});
