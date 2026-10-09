import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider, type Locale } from "../../shared/i18n";
import type { FlowDocument } from "../../shared/types";
import { FlowsPage } from "./FlowsPage";

const flow: FlowDocument = {
  flow_id: "auto-guard", name: "Auto Guard", enabled: true, brief: "Inspect production.",
  path: "lumon/flows/auto-guard.md", valid: true, error: null,
  content: '# Auto Guard\n\nRead-only review.',
  schedule_enabled: true, schedule_expression: "0 10 * * 1-5",
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

async function renderFlow(document: FlowDocument, locale: Locale = "en") {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", locale);
  const requests = vi.fn(async (path: string) => {
    if (path.endsWith("/flows")) return new Response(JSON.stringify([document]));
    if (path.endsWith("/flows/auto-guard")) return new Response(JSON.stringify(document));
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", requests);
  const container = window.document.createElement("div");
  const root = createRoot(container);
  const onDirtyChange = vi.fn();
  const onError = vi.fn();
  await act(async () => root.render(<I18nProvider><FlowsPage
    workspaceId="workspace-one" initialDocumentId={document.flow_id}
    onDirtyChange={onDirtyChange} onNotice={vi.fn()} onError={onError}
  /></I18nProvider>));
  return { container, root, onDirtyChange, onError, requests };
}

it.each(["en", "zh-CN", "zh-TW"] as const)("keeps scheduling above the document and saves it independently in %s", async (locale) => {
  const save = vi.spyOn(dashboardApi, "updateFlowSchedule").mockImplementation(async (_workspaceId, _flowId, enabled, expression) => (
    { ...flow, schedule_enabled: enabled, schedule_expression: expression }
  ));
  const { container, root, onDirtyChange, onError, requests } = await renderFlow(flow, locale);
  try {
    const panel = container.querySelector<HTMLElement>(".flow-schedule-panel")!;
    const preview = container.querySelector<HTMLElement>(".flow-markdown-preview")!;
    const input = panel.querySelector<HTMLInputElement>("#flow-schedule-expression")!;
    const toggle = panel.querySelector<HTMLInputElement>('[role="switch"]')!;
    const saveSchedule = panel.querySelector<HTMLButtonElement>(".settings-actions button")!;
    const saveDocument = container.querySelector<HTMLButtonElement>(".flow-editor-actions .button-primary")!;
    expect(panel.closest(".flow-editor-panel")).not.toBeNull();
    expect(panel.classList.contains("panel")).toBe(false);
    expect(panel.compareDocumentPosition(preview) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
    expect(panel.querySelector(".status-pill")).toBeNull();
    expect(toggle.checked).toBe(true);
    expect(saveSchedule.disabled).toBe(true);
    expect(saveDocument.disabled).toBe(true);

    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "0 11 * * 1-5");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(saveSchedule.disabled).toBe(false);
    expect(saveDocument.disabled).toBe(true);
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    await act(async () => container.querySelectorAll<HTMLButtonElement>(".flow-view-toggle button")[1].click());
    expect(container.querySelector(".flow-editor")).not.toBeNull();
    expect(input.value).toBe("0 11 * * 1-5");
    await act(async () => container.querySelectorAll<HTMLButtonElement>(".flow-view-toggle button")[0].click());
    expect(input.value).toBe("0 11 * * 1-5");
    expect(save).not.toHaveBeenCalled();

    save.mockRejectedValueOnce(new Error("Schedule could not be saved."));
    await act(async () => saveSchedule.click());
    expect(onError).toHaveBeenCalledWith("Schedule could not be saved.");
    expect(input.value).toBe("0 11 * * 1-5");
    expect(saveSchedule.disabled).toBe(false);
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    await act(async () => saveSchedule.click());
    expect(save).toHaveBeenLastCalledWith("workspace-one", "auto-guard", true, "0 11 * * 1-5");
    expect(saveSchedule.disabled).toBe(true);
    expect(onDirtyChange).toHaveBeenLastCalledWith(false);

    await act(async () => toggle.click());
    expect(toggle.checked).toBe(false);
    expect(panel.querySelector(".status-pill")).toBeNull();
    await act(async () => saveSchedule.click());
    expect(save).toHaveBeenLastCalledWith("workspace-one", "auto-guard", false, "0 11 * * 1-5");

    await act(async () => container.querySelectorAll<HTMLButtonElement>(".flow-view-toggle button")[1].click());
    const editor = container.querySelector<HTMLTextAreaElement>(".flow-editor")!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(editor, "# Updated plan");
      editor.dispatchEvent(new Event("input", { bubbles: true }));
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "0 12 * * 1-5");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => saveSchedule.click());
    expect(editor.value).toBe("# Updated plan");
    expect(saveDocument.disabled).toBe(false);
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
    expect(requests).toHaveBeenCalledTimes(2);
  } finally {
    await act(async () => root.unmount());
  }
});

it.each([false, true])("keeps disabled or invalid workflows from being scheduled (valid=%s)", async (valid) => {
  const save = vi.spyOn(dashboardApi, "updateFlowSchedule");
  const { container, root } = await renderFlow({ ...flow, enabled: false, valid });
  try {
    const toggle = container.querySelector<HTMLInputElement>('.flow-schedule-panel [role="switch"]');
    if (valid) {
      expect(toggle?.disabled).toBe(true);
      expect(container.querySelector(".flow-schedule-panel")?.textContent).toContain("Enable this Workflow before scheduling it.");
    } else {
      expect(container.querySelector(".flow-schedule-panel")).toBeNull();
    }
    expect(save).not.toHaveBeenCalled();
  } finally {
    await act(async () => root.unmount());
  }
});
