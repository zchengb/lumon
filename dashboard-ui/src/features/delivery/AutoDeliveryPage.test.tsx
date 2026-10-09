import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { I18nProvider } from "../../shared/i18n";
import { dashboardApi } from "../../app/api";
import { AutoDeliveryPage } from "./AutoDeliveryPage";

it.each(["en", "zh-CN", "zh-TW"] as const)("shows delivery execution history without configuration in %s", async (locale) => {
  const container = document.createElement("div");
  const root = createRoot(container);
  const history = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [], polls: [] });
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", locale);
    await act(async () => root.render(<I18nProvider><AutoDeliveryPage workspaceId="workspace-id" onError={vi.fn()} /></I18nProvider>));
    expect(history).toHaveBeenCalledWith("workspace-id");
    expect(container.querySelector("h1")?.textContent).toBe("Auto Delivery");
    expect(container.querySelector(".delivery-progress-panel")).not.toBeNull();
    expect(container.querySelector(".settings-panel")).toBeNull();
    expect(container.querySelector("#auto-delivery-hooks")).toBeNull();
    expect(container.querySelector('[role="switch"]')).toBeNull();
  } finally {
    await act(async () => root.unmount());
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.removeItem("lumon.locale");
  }
});
