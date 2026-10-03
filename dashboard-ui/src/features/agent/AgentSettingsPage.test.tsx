import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider, LanguagePicker } from "../../shared/i18n";
import type { AgentSettings, CodexCliStatus } from "../../shared/types";
import { AgentSettingsPage } from "./AgentSettingsPage";

const settings: AgentSettings = {
  enabled: true, default_workspace_id: null, agent_provider: "codex", agent_model: "gpt-5.6-luna",
  agent_reasoning_effort: "max", feishu_app_id: "", feishu_app_configured: false,
  feishu_app_secret_masked: null, observability: {
    enabled: false, provider: "langfuse", base_url: "https://cloud.langfuse.com", sample_rate: 1,
    public_key_configured: false, secret_key_configured: false, public_key_masked: null, secret_key_masked: null,
  },
};
const currentCli: CodexCliStatus = {
  status: "up_to_date", binary_path: "/test/codex", installed_version: "0.160.0", latest_version: "0.160.0",
};

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "getCodexCliStatus").mockResolvedValue(currentCli);
  vi.spyOn(dashboardApi, "listAgentModels").mockResolvedValue([{
    model: "gpt-5.6-luna", display_name: "GPT-5.6 Luna", description: "Current model",
    default_reasoning_effort: "medium", supported_reasoning_efforts: ["medium", "max"],
  }]);
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

async function mount() {
  const container = document.createElement("div");
  const root = createRoot(container);
  const onDirtyChange = vi.fn();
  const onSave = vi.fn().mockResolvedValue(true);
  await act(async () => root.render(<I18nProvider><LanguagePicker /><AgentSettingsPage settings={settings} workspaces={[]} onSave={onSave} onDirtyChange={onDirtyChange} /></I18nProvider>));
  return {
    container, onDirtyChange, onSave,
    model: () => container.querySelector<HTMLSelectElement>("#agent-model")!,
    effort: () => container.querySelector<HTMLSelectElement>("#agent-reasoning")!,
    refresh: async () => { await act(async () => container.querySelector<HTMLButtonElement>(".model-picker-controls button")!.click()); },
    unmount: async () => { await act(async () => root.unmount()); },
  };
}

it("merges the installed version and update badge into the read-only provider field", async () => {
  const check = vi.mocked(dashboardApi.getCodexCliStatus).mockResolvedValue({
    ...currentCli, status: "update_available", installed_version: "0.156.1",
  });
  const view = await mount();
  try {
    const provider = view.container.querySelector<HTMLInputElement>("#agent-provider")!;
    const notice = provider.parentElement!.querySelector(".codex-cli-notice")!;
    expect(provider.value).toBe("codex");
    expect(provider.readOnly).toBe(true);
    expect(view.container.querySelector('label[for="agent-provider"]')).not.toBeNull();
    expect(notice.textContent).toContain("0.156.1");
    expect(notice.textContent).toContain("Update available");
    expect(notice.getAttribute("role")).toBe("status");
    expect(notice.querySelectorAll("a, button, p")).toHaveLength(0);
    expect(notice.textContent).not.toContain("Codex CLI");
    expect(notice.textContent).not.toContain("0.160.0");
    expect(notice.textContent).not.toContain("/test/codex");
    expect(view.model().closest(".model-picker-controls")!.parentElement!.querySelector(".codex-cli-notice")).toBeNull();
    expect(view.container.querySelector("#agent-model-help")).toBeNull();
    expect(view.container.textContent).not.toContain("Current model");
    expect(check).toHaveBeenCalledWith(false);
    expect(view.model().value).toBe("gpt-5.6-luna");
    expect(view.effort().value).toBe("max");
    expect(view.onDirtyChange).not.toHaveBeenCalledWith(true);
    expect(view.onSave).not.toHaveBeenCalled();
    expect(view.container.querySelector<HTMLButtonElement>(".agent-settings-actions button")?.disabled).toBe(true);
    await act(async () => {
      const language = view.container.querySelector<HTMLSelectElement>(".language-picker select")!;
      language.value = "zh-TW";
      language.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(notice.textContent).toContain("可升級");
    expect(check).toHaveBeenCalledTimes(1);
  } finally { await view.unmount(); }
});

it("refreshes provider updates with the model catalog without changing the draft", async () => {
  const check = vi.mocked(dashboardApi.getCodexCliStatus)
    .mockResolvedValueOnce({ ...currentCli, status: "update_available", installed_version: "0.156.1" })
    .mockResolvedValueOnce(currentCli)
    .mockResolvedValue({ ...currentCli, status: "update_available", latest_version: "0.161.0" });
  const view = await mount();
  try {
    await view.refresh();
    expect(check).toHaveBeenLastCalledWith(true);
    expect(view.container.querySelector(".codex-cli-notice")).toBeNull();
    await view.refresh();
    expect(check).toHaveBeenCalledTimes(3);
    expect(check).toHaveBeenLastCalledWith(true);
    expect(dashboardApi.listAgentModels).toHaveBeenCalledTimes(3);
    expect(view.container.querySelector(".agent-provider-control .codex-cli-notice")?.textContent).toContain("0.160.0");
    expect(view.model().value).toBe("gpt-5.6-luna");
    expect(view.effort().value).toBe("max");
    expect(view.onDirtyChange).not.toHaveBeenCalledWith(true);
    expect(view.onSave).not.toHaveBeenCalled();
  } finally { await view.unmount(); }
});

it("hides a stale update badge if checking fails and permits retry", async () => {
  vi.mocked(dashboardApi.getCodexCliStatus)
    .mockResolvedValueOnce({ ...currentCli, status: "update_available" })
    .mockRejectedValueOnce(new Error("secret-value"))
    .mockResolvedValueOnce({ ...currentCli, status: "update_available" });
  const view = await mount();
  try {
    expect(view.container.querySelector(".codex-cli-notice")).not.toBeNull();
    await view.refresh();
    expect(view.container.querySelector(".codex-cli-notice")).toBeNull();
    expect(view.container.textContent).not.toContain("secret-value");
    expect(view.model().disabled).toBe(false);
    await view.refresh();
    expect(view.container.querySelector(".agent-provider-control .codex-cli-notice")?.textContent).toContain("0.160.0");
    expect(view.onDirtyChange).not.toHaveBeenCalledWith(true);
  } finally { await view.unmount(); }
});

it.each(["up_to_date", "check_failed", "cli_unavailable"] as const)("omits the CLI notice for %s", async (status) => {
  vi.mocked(dashboardApi.getCodexCliStatus).mockResolvedValue({ ...currentCli, status });
  const view = await mount();
  try {
    expect(view.container.querySelector(".codex-cli-notice")).toBeNull();
    expect(view.container.querySelector<HTMLInputElement>("#agent-provider")?.value).toBe("codex");
    expect(view.model().value).toBe("gpt-5.6-luna");
  } finally { await view.unmount(); }
});

it("ignores a late update result after unmounting", async () => {
  let resolve!: (status: CodexCliStatus) => void;
  vi.mocked(dashboardApi.getCodexCliStatus).mockReturnValue(new Promise((ready) => { resolve = ready; }));
  const view = await mount();
  expect(view.container.querySelector(".codex-cli-notice")).toBeNull();
  await view.unmount();
  await act(async () => resolve(currentCli));
  expect(view.container.textContent).toBe("");
  expect(view.onDirtyChange).not.toHaveBeenCalledWith(true);
});
