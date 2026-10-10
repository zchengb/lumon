import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider, LanguagePicker } from "../../shared/i18n";
import type { AgentSettings, AgentSettingsUpdate, CodexCliStatus, WorkspaceListItem } from "../../shared/types";
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

async function mount(initialSettings = settings, workspaces: WorkspaceListItem[] = []) {
  const container = document.createElement("div");
  const root = createRoot(container);
  const onDirtyChange = vi.fn();
  const onSave = vi.fn<(update: AgentSettingsUpdate) => Promise<boolean>>().mockResolvedValue(true);
  async function rerender(nextSettings: AgentSettings): Promise<void> {
    await act(async () => root.render(<I18nProvider><LanguagePicker /><AgentSettingsPage settings={nextSettings} workspaces={workspaces} onSave={onSave} onDirtyChange={onDirtyChange} /></I18nProvider>));
  }
  await rerender(initialSettings);
  return {
    container, onDirtyChange, onSave, rerender,
    panel: (section: "agent" | "langfuse") => container.querySelector<HTMLElement>(`section[aria-labelledby="agent-${section === "agent" ? "runtime" : "langfuse"}-title"]`)!,
    saveButton: (section: "agent" | "langfuse") => container.querySelector<HTMLButtonElement>(`button[aria-label="Save ${section === "agent" ? "Agent" : "Langfuse Cloud"}"]`)!,
    field: (selector: string) => container.querySelector<HTMLInputElement>(selector)!,
    edit: async (selector: string, value: string) => {
      await act(async () => {
        const input = container.querySelector<HTMLInputElement>(selector)!;
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
    },
    model: () => container.querySelector<HTMLSelectElement>("#agent-model")!,
    effort: () => container.querySelector<HTMLSelectElement>("#agent-reasoning")!,
    refresh: async () => { await act(async () => container.querySelector<HTMLButtonElement>(".model-picker-controls button")!.click()); },
    unmount: async () => { await act(async () => root.unmount()); },
  };
}

const workspaceOptions: WorkspaceListItem[] = [
  { workspace_id: "ready-id", name: "MBPass", health: "ready", path: "/test/mbpass", registered_at: "2026-10-10T00:00:00Z", detail: "Available." },
  { workspace_id: "missing-id", name: "workspace", health: "missing", path: "/test/missing", registered_at: "2026-10-10T00:00:00Z", detail: "Missing directory." },
  { workspace_id: "invalid-id", name: "workspace", health: "invalid", path: "/test/invalid", registered_at: "2026-10-10T00:00:00Z", detail: "Invalid manifest." },
];

it.each([
  ["en", "Path missing", "Invalid configuration"],
  ["zh-CN", "路径不存在", "配置异常"],
  ["zh-TW", "路徑不存在", "設定異常"],
])("labels and disables unhealthy default Workspace options in %s", async (locale, missingLabel, invalidLabel) => {
  localStorage.setItem("lumon.locale", locale);
  const view = await mount({ ...settings, default_workspace_id: "ready-id" }, workspaceOptions);
  try {
    const picker = view.container.querySelector<HTMLSelectElement>("#agent-default-workspace")!;
    expect(picker.value).toBe("ready-id");
    expect(Array.from(picker.options, (option) => [option.textContent, option.disabled])).toEqual([
      [picker.options[0]!.textContent, false],
      ["MBPass", false],
      [`workspace · ${missingLabel}`, true],
      [`workspace · ${invalidLabel}`, true],
    ]);
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(false);
    expect(view.onSave).not.toHaveBeenCalled();
  } finally { await view.unmount(); }
});

it.each(["missing-id", "invalid-id", "unregistered-id"])("preserves an unavailable saved default %s until the user chooses a healthy Workspace", async (workspaceId) => {
  const initialSettings = { ...settings, default_workspace_id: workspaceId };
  const view = await mount(initialSettings, workspaceOptions);
  try {
    const picker = view.container.querySelector<HTMLSelectElement>("#agent-default-workspace")!;
    expect(picker.value).toBe(workspaceId);
    expect(picker.selectedOptions[0]!.disabled).toBe(true);
    expect(view.saveButton("agent").disabled).toBe(true);
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(false);
    expect(view.onSave).not.toHaveBeenCalled();
    await act(async () => { picker.value = "ready-id"; picker.dispatchEvent(new Event("change", { bubbles: true })); });
    await act(async () => view.saveButton("agent").click());
    expect(view.onSave.mock.calls[0][0].default_workspace_id).toBe("ready-id");
    expect(view.onSave.mock.calls[0][0].observability.base_url).toBe(settings.observability.base_url);
  } finally { await view.unmount(); }
});

it.each(["ready", "missing", "invalid"] as const)("offers automatic sole-Workspace selection only for a healthy registration (%s)", async (health) => {
  const view = await mount(settings, [{ ...workspaceOptions[0]!, health }]);
  try {
    const picker = view.container.querySelector<HTMLSelectElement>("#agent-default-workspace")!;
    expect(picker.options[0]!.textContent).toBe(health === "ready" ? "Use the only Workspace automatically" : "No default Workspace");
    expect(picker.value).toBe("");
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally { await view.unmount(); }
});

it.each([
  ["en", "Model and reasoning effort changes apply to the next request. Other settings require restarting Agent."],
  ["zh-CN", "模型和 Reasoning effort 保存后从下一次请求生效；其他配置仍需重启 Agent。"],
  ["zh-TW", "模型與 Reasoning effort 儲存後從下一次請求生效；其他設定仍需重新啟動 Agent。"],
])("explains model hot reload in %s", async (locale, helpText) => {
  localStorage.setItem("lumon.locale", locale);
  const view = await mount();
  try {
    expect(view.panel("agent").querySelector(".field-help")).toBeNull();
    const help = document.getElementById("agent-apply-help")!;
    expect(help.textContent).toBe(helpText);
    expect(help.hidden).toBe(true);
    const button = view.panel("agent").querySelector<HTMLButtonElement>(".field-help-toggle")!;
    await act(async () => button.click());
    expect(help.hidden).toBe(false);
    await act(async () => document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })));
    expect(help.hidden).toBe(true);
    expect(view.onSave).not.toHaveBeenCalled();
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally { await view.unmount(); }
});

it("keeps Langfuse guidance in a title tooltip while model errors remain visible", async () => {
  vi.mocked(dashboardApi.listAgentModels).mockRejectedValue(new Error("Unavailable"));
  const view = await mount();
  try {
    const panel = view.panel("langfuse");
    expect(panel.querySelector(".settings-description")).toBeNull();
    const help = document.getElementById("agent-langfuse-help")!;
    expect(help.hidden).toBe(true);
    expect(help.textContent).toContain("lifecycle trace");
    await act(async () => panel.querySelector<HTMLButtonElement>(".field-help-toggle")!.click());
    expect(help.hidden).toBe(false);
    expect(view.panel("agent").querySelector('[role="alert"]')?.textContent).toContain("model");
    expect(view.onSave).not.toHaveBeenCalled();
  } finally { await view.unmount(); }
});

it("places one Save action inside each panel and tracks changes independently", async () => {
  const view = await mount();
  try {
    expect(view.container.querySelectorAll(".agent-settings-actions")).toHaveLength(2);
    for (const section of ["agent", "langfuse"] as const) {
      expect(view.saveButton(section).closest("section")).toBe(view.panel(section));
      expect(view.saveButton(section).textContent).toBe("Save");
      expect(view.saveButton(section).disabled).toBe(true);
    }
    expect(view.container.querySelector(".page-stack > .settings-actions")).toBeNull();
    await view.edit("#langfuse-base-url", "https://langfuse.test");
    expect(view.saveButton("agent").disabled).toBe(true);
    expect(view.saveButton("langfuse").disabled).toBe(false);
    expect(view.panel("agent").querySelector(".unsaved-label")).toBeNull();
    expect(view.panel("langfuse").querySelector(".unsaved-label")?.textContent).toBe("Unsaved changes");
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(true);
    await view.edit("#langfuse-base-url", settings.observability.base_url);
    expect(view.saveButton("langfuse").disabled).toBe(true);
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally { await view.unmount(); }
});

it.each(["agent", "langfuse"] as const)("saves %s without submitting or discarding the other panel's draft", async (section) => {
  const view = await mount();
  try {
    await view.edit("#feishu-app-id", "cli_draft");
    await view.edit("#feishu-app-secret", "app-draft-secret");
    await view.edit("#langfuse-base-url", "https://draft.langfuse.test");
    await view.edit("#langfuse-public-key", "public-draft-key");
    await view.edit("#langfuse-secret-key", "secret-draft-key");
    await act(async () => view.saveButton(section).click());
    expect(view.onSave).toHaveBeenCalledTimes(1);
    const update = view.onSave.mock.calls[0][0];
    if (section === "agent") {
      expect(update.feishu_app_id).toBe("cli_draft");
      expect(update.feishu_app_secret).toBe("app-draft-secret");
      expect(update.observability).toEqual({ enabled: false, base_url: settings.observability.base_url, sample_rate: 1 });
      await view.rerender({ ...settings, feishu_app_id: "cli_draft", feishu_app_secret_masked: "app…cret" });
      expect(view.field("#feishu-app-secret").value).toBe("");
      expect(view.field("#langfuse-base-url").value).toBe("https://draft.langfuse.test");
      expect(view.field("#langfuse-public-key").value).toBe("public-draft-key");
      expect(view.field("#langfuse-secret-key").value).toBe("secret-draft-key");
    } else {
      expect(update.feishu_app_id).toBe(settings.feishu_app_id);
      expect(update.feishu_app_secret).toBeUndefined();
      expect(update.observability).toMatchObject({ base_url: "https://draft.langfuse.test", public_key: "public-draft-key", secret_key: "secret-draft-key" });
      await view.rerender({ ...settings, observability: { ...settings.observability, base_url: "https://draft.langfuse.test", public_key_masked: "pub…key", secret_key_masked: "sec…key" } });
      expect(view.field("#langfuse-public-key").value).toBe("");
      expect(view.field("#langfuse-secret-key").value).toBe("");
      expect(view.field("#feishu-app-id").value).toBe("cli_draft");
      expect(view.field("#feishu-app-secret").value).toBe("app-draft-secret");
    }
    expect(view.saveButton(section).disabled).toBe(true);
    expect(view.saveButton(section === "agent" ? "langfuse" : "agent").disabled).toBe(false);
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(true);
  } finally { await view.unmount(); }
});

it.each(["agent", "langfuse"] as const)("keeps the %s draft after a failed save", async (section) => {
  const view = await mount();
  view.onSave.mockResolvedValue(false);
  try {
    await view.edit("#feishu-app-secret", "app-draft-secret");
    await view.edit("#langfuse-secret-key", "langfuse-draft-secret");
    await act(async () => view.saveButton(section).click());
    expect(view.field("#feishu-app-secret").value).toBe("app-draft-secret");
    expect(view.field("#langfuse-secret-key").value).toBe("langfuse-draft-secret");
    expect(view.saveButton("agent").disabled).toBe(false);
    expect(view.saveButton("langfuse").disabled).toBe(false);
    expect(view.panel(section).getAttribute("aria-busy")).toBe("false");
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(true);
  } finally { await view.unmount(); }
});

it.each(["agent", "langfuse"] as const)("clears a successful %s credential edit even if its saved mask is unchanged", async (section) => {
  const view = await mount();
  try {
    const selector = section === "agent" ? "#feishu-app-secret" : "#langfuse-secret-key";
    await view.edit(selector, "credential-replacement");
    await act(async () => view.saveButton(section).click());
    await view.rerender({ ...settings, observability: { ...settings.observability } });
    expect(view.field(selector).value).toBe("");
    expect(view.saveButton(section).disabled).toBe(true);
    expect(view.onDirtyChange).toHaveBeenLastCalledWith(false);
  } finally { await view.unmount(); }
});

it.each(["agent", "langfuse"] as const)("serializes a pending %s save and leaves the other panel editable", async (section) => {
  const view = await mount();
  let finish!: (saved: boolean) => void;
  view.onSave.mockReturnValue(new Promise((resolve) => { finish = resolve; }));
  try {
    await view.edit("#feishu-app-secret", "app-draft-secret");
    await view.edit("#langfuse-secret-key", "langfuse-draft-secret");
    await act(async () => view.saveButton(section).click());
    expect(view.saveButton("agent").disabled).toBe(true);
    expect(view.saveButton("langfuse").disabled).toBe(true);
    expect(view.panel(section).getAttribute("aria-busy")).toBe("true");
    expect(view.panel(section).querySelector<HTMLFieldSetElement>("fieldset")?.disabled).toBe(true);
    const other = section === "agent" ? "langfuse" : "agent";
    expect(view.panel(other).querySelector<HTMLFieldSetElement>("fieldset")?.disabled).toBe(false);
    expect(view.panel(other).querySelector(".spin")).toBeNull();
    await act(async () => view.saveButton(other).click());
    expect(view.onSave).toHaveBeenCalledTimes(1);
    await view.edit(section === "agent" ? "#langfuse-secret-key" : "#feishu-app-secret", "edited-while-saving");
    await act(async () => finish(true));
    expect(view.field(section === "agent" ? "#langfuse-secret-key" : "#feishu-app-secret").value).toBe("edited-while-saving");
    expect(view.saveButton(other).disabled).toBe(false);
  } finally { await view.unmount(); }
});

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
