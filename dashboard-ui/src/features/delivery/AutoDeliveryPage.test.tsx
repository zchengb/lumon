import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "../../shared/i18n";
import { dashboardApi } from "../../app/api";
import type { WorkspaceSettings } from "../../shared/types";
import { AutoDeliveryPage } from "./AutoDeliveryPage";

it.each(["en", "zh-CN", "zh-TW"] as const)("saves a multiline trigger prompt and supports clearing it while disabled in %s", async (locale) => {
  const settings: WorkspaceSettings = {
    workspace_id: "workspace-id",
    feishu_webhook: { enabled: true, configured: true, masked_url: null },
    auto_delivery: { enabled: false, trigger_hooks: ["jira.delivery_ready", "mail.delivery_ready"], schedule_expression: "*/5 * * * *" },
    auto_scan: { enabled: false, trigger_hooks: [], schedule_expression: "0 12 * * 1-5", lookback_days: 7, workflow_description: "Review confirmed bugs only." },
  };
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onSave = vi.fn().mockResolvedValue(true);
  const onDirtyChange = vi.fn();
  const prompt = "Check approved Stories.\n\n1. Verify the requirements.\n2. Follow the delivery workflow.";
  try {
    vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [], polls: [] });
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", locale);
    const render = async (next: WorkspaceSettings) => act(async () => root.render(<I18nProvider><AutoDeliveryPage
      settings={next} onSave={onSave} onDirtyChange={onDirtyChange} onError={vi.fn()}
    /></I18nProvider>));
    await render(settings);
    const field = container.querySelector<HTMLTextAreaElement>("#auto-delivery-hooks")!;
    const save = container.querySelector<HTMLButtonElement>(".settings-actions button")!;
    expect(field.value).toBe("jira.delivery_ready\nmail.delivery_ready");
    expect(field.maxLength).toBe(8000);
    expect(field.getAttribute("aria-describedby")).toBe("auto-delivery-hooks-help");
    expect(field.classList.contains("mono")).toBe(false);
    expect(field.placeholder).not.toBe("jira.delivery_ready");
    expect(save.disabled).toBe(true);

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
