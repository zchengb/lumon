import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { I18nProvider, type Locale } from "../../shared/i18n";
import type { WorkspaceSettings } from "../../shared/types";
import { SettingsPage } from "./SettingsPage";

const settings: WorkspaceSettings = {
  workspace_id: "test-workspace",
  feishu_webhook: { enabled: true, configured: true, masked_url: "https://example.test/…1234" },
  auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "", jira_site: "", trigger_jql: "", publish_mode: "local", target_branch: "" },
  auto_scan: { enabled: false, lookback_days: 7, trigger_hooks: [], schedule_expression: "", workflow_description: "" },
};

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

it.each<{ locale: Locale; label: string }>([
  { locale: "zh-CN", label: "保存" },
  { locale: "zh-TW", label: "儲存" },
  { locale: "en", label: "Save" },
])("uses the short Webhook save label in $locale without changing save behavior", async ({ locale, label }) => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", locale);
  const container = document.createElement("div");
  const root = createRoot(container);
  const onSave = vi.fn().mockResolvedValue(true);
  const onTest = vi.fn();
  const onDirtyChange = vi.fn();
  try {
    await act(async () => root.render(<I18nProvider><SettingsPage settings={settings} onSave={onSave} onTest={onTest} onDirtyChange={onDirtyChange} /></I18nProvider>));
    const saveButton = container.querySelector<HTMLButtonElement>(".settings-actions .button-primary")!;
    expect(saveButton.textContent).toBe(label);
    expect(saveButton.disabled).toBe(true);
    await act(async () => container.querySelector<HTMLInputElement>('[role="switch"]')!.click());
    expect(saveButton.disabled).toBe(false);
    await act(async () => saveButton.click());
    expect(onSave).toHaveBeenCalledExactlyOnceWith({ feishu_webhook: { enabled: false } });
    expect(onTest).not.toHaveBeenCalled();
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally {
    await act(async () => root.unmount());
  }
});
