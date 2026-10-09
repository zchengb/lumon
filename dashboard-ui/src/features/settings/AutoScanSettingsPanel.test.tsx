import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "../../shared/i18n";
import type { WorkspaceSettings } from "../../shared/types";
import { AutoScanSettingsPanel } from "./AutoScanSettingsPanel";

it.each(["en", "zh-CN", "zh-TW"] as const)("saves a multiline completion prompt and supports clearing it in %s", async (locale) => {
  const settings: WorkspaceSettings = {
    workspace_id: "workspace-id",
    feishu_webhook: { enabled: true, configured: true, masked_url: null },
    auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "*/5 * * * *", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" },
    auto_scan: { enabled: true, trigger_hooks: ["twg.create_bug", "mail.scan_done"], schedule_expression: "0 12 * * 1-5", lookback_days: 7, workflow_description: "Review confirmed bugs only." },
  };
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onSave = vi.fn().mockResolvedValue(true);
  const onDirtyChange = vi.fn();
  const prompt = "Create verified Jira Bugs.\n\n1. Reuse duplicates.\n2. Include code evidence.";
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", locale);
    const render = async (next: WorkspaceSettings) => act(async () => root.render(<I18nProvider><AutoScanSettingsPanel
      settings={next} onSave={onSave} onDirtyChange={onDirtyChange}
    /></I18nProvider>));
    await render(settings);
    expect(container.querySelector("#auto-scan-description")).toBeNull();
    const field = container.querySelector<HTMLTextAreaElement>("#auto-scan-hooks")!;
    const save = container.querySelector<HTMLButtonElement>(".settings-actions button")!;
    expect(field.value).toBe("twg.create_bug\nmail.scan_done");
    expect(field.maxLength).toBe(8000);
    expect(field.getAttribute("aria-describedby")).toBeNull();
    expect(container.querySelector("#auto-scan-hooks-help")).toBeNull();
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
      auto_scan: { enabled: true, lookback_days: 7, schedule_expression: "0 12 * * 1-5", trigger_hooks: [prompt] },
    });
    await render({ ...settings, auto_scan: { ...settings.auto_scan, trigger_hooks: [prompt] } });
    expect(field.value).toBe(prompt);
    expect(save.disabled).toBe(true);

    await fill(" \n ");
    await act(async () => save.click());
    expect(onSave).toHaveBeenLastCalledWith({
      feishu_webhook: { enabled: true },
      auto_scan: { enabled: true, lookback_days: 7, schedule_expression: "0 12 * * 1-5", trigger_hooks: [] },
    });
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally {
    await act(async () => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
    localStorage.removeItem("lumon.locale");
  }
});
