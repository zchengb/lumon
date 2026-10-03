import { act, useState } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider, LanguagePicker } from "../../shared/i18n";
import type { AgentModel } from "../../shared/types";
import { AgentModelPicker } from "./AgentModelPicker";

const models: AgentModel[] = [
  { model: "gpt-5.6-luna", display_name: "GPT-5.6 Luna", description: "Current model", default_reasoning_effort: "medium", supported_reasoning_efforts: ["medium", "max"] },
  { model: "future-model", display_name: "Future model", description: "New model", default_reasoning_effort: "none", supported_reasoning_efforts: ["none", "adaptive"] },
];

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

async function mount(onChange: (model: string, effort: string) => void) {
  const container = document.createElement("div");
  const root = createRoot(container);
  function Harness(): React.JSX.Element {
    const [model, setModel] = useState("gpt-5.6-luna");
    const [effort, setEffort] = useState("max");
    return <I18nProvider><LanguagePicker /><AgentModelPicker model={model} reasoningEffort={effort} onChange={(nextModel, nextEffort) => {
      onChange(nextModel, nextEffort); setModel(nextModel); setEffort(nextEffort);
    }} /></I18nProvider>;
  }
  await act(async () => root.render(<Harness />));
  return {
    container,
    model: () => container.querySelector<HTMLSelectElement>("#agent-model")!,
    effort: () => container.querySelector<HTMLSelectElement>("#agent-reasoning")!,
    refresh: () => container.querySelector<HTMLButtonElement>(".model-picker-controls button")!,
    select: async (selector: string, value: string) => {
      await act(async () => {
        const select = container.querySelector<HTMLSelectElement>(selector)!;
        select.value = value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      });
    },
    unmount: async () => { await act(async () => root.unmount()); },
  };
}

it("loads provider models without changing the saved model or effort", async () => {
  let resolve!: (models: AgentModel[]) => void;
  const list = vi.spyOn(dashboardApi, "listAgentModels").mockReturnValue(new Promise((ready) => { resolve = ready; }));
  const onChange = vi.fn();
  const view = await mount(onChange);
  try {
    expect(view.model().value).toBe("gpt-5.6-luna");
    expect(view.effort().value).toBe("max");
    expect(view.refresh().disabled).toBe(true);
    expect(view.container.querySelector('[role="status"]')?.textContent).toContain("Loading models");
    expect(view.model().getAttribute("aria-describedby")).toBe("agent-model-help");
    await act(async () => resolve(models));
    expect(Array.from(view.model().options, (option) => option.text)).toEqual(["GPT-5.6 Luna", "Future model"]);
    expect(view.refresh().disabled).toBe(false);
    expect(view.effort().value).toBe("max");
    expect(onChange).not.toHaveBeenCalled();
    await view.select(".language-picker select", "zh-TW");
    expect(view.refresh().getAttribute("aria-label")).toBe("重新整理模型列表");
    expect(list).toHaveBeenCalledTimes(1);
  } finally { await view.unmount(); }
});

it("uses the model's supported efforts and replaces only incompatible selections", async () => {
  vi.spyOn(dashboardApi, "listAgentModels").mockResolvedValue(models);
  const onChange = vi.fn();
  const view = await mount(onChange);
  try {
    await view.select("#agent-model", "future-model");
    expect(onChange).toHaveBeenLastCalledWith("future-model", "none");
    expect(Array.from(view.effort().options, (option) => option.value)).toEqual(["none", "adaptive"]);
    await view.select("#agent-reasoning", "adaptive");
    expect(onChange).toHaveBeenLastCalledWith("future-model", "adaptive");
    await view.select("#agent-model", "gpt-5.6-luna");
    expect(onChange).toHaveBeenLastCalledWith("gpt-5.6-luna", "medium");
    await view.select("#agent-reasoning", "max");
    await view.select("#agent-model", "gpt-5.6-luna");
    expect(onChange).toHaveBeenLastCalledWith("gpt-5.6-luna", "max");
  } finally { await view.unmount(); }
});

it("keeps the existing catalog and selection on refresh failure, and permits retry", async () => {
  const list = vi.spyOn(dashboardApi, "listAgentModels")
    .mockResolvedValueOnce(models)
    .mockRejectedValueOnce(new Error("provider failure"))
    .mockResolvedValueOnce([models[1]]);
  const onChange = vi.fn();
  const view = await mount(onChange);
  try {
    await act(async () => view.refresh().click());
    expect(view.container.querySelector('[role="alert"]')?.textContent).toContain("Your selection is unchanged");
    expect(view.model().options).toHaveLength(2);
    expect(view.model().value).toBe("gpt-5.6-luna");
    expect(view.effort().value).toBe("max");
    await act(async () => view.refresh().click());
    expect(view.container.querySelector('[role="alert"]')).toBeNull();
    expect(view.container.textContent).toContain("Your current model is kept");
    expect(view.model().value).toBe("gpt-5.6-luna");
    expect(Array.from(view.model().options, (option) => option.value)).toEqual(["gpt-5.6-luna", "future-model"]);
    expect(list).toHaveBeenCalledTimes(3);
    expect(onChange).not.toHaveBeenCalled();
  } finally { await view.unmount(); }
});

it("keeps configuration editable if the initial catalog is unavailable or empty", async () => {
  vi.spyOn(dashboardApi, "listAgentModels").mockRejectedValueOnce(new Error("unavailable")).mockResolvedValueOnce([]);
  const onChange = vi.fn();
  const view = await mount(onChange);
  try {
    expect(view.model().disabled).toBe(false);
    expect(view.effort().disabled).toBe(false);
    expect(view.model().value).toBe("gpt-5.6-luna");
    await act(async () => view.refresh().click());
    expect(view.model().options).toHaveLength(1);
    expect(view.effort().value).toBe("max");
    expect(onChange).not.toHaveBeenCalled();
  } finally { await view.unmount(); }
});

it("ignores a catalog result after the picker is unmounted", async () => {
  let resolve!: (models: AgentModel[]) => void;
  vi.spyOn(dashboardApi, "listAgentModels").mockReturnValue(new Promise((ready) => { resolve = ready; }));
  const onChange = vi.fn();
  const view = await mount(onChange);
  await view.unmount();
  await act(async () => resolve(models));
  expect(view.container.textContent).toBe("");
  expect(onChange).not.toHaveBeenCalled();
});
