import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider, translate } from "../../shared/i18n";
import type { VisualEnvironmentSnapshot } from "../../shared/types";
import { VisualEnvironmentPanel } from "./VisualEnvironmentPanel";

const snapshot: VisualEnvironmentSnapshot = {
  checked_at: "2026-10-22T01:00:00Z", application_status: "unverified",
  environments: [
    { platform: "ios", status: "ready", running: false, checks: [{ name: "ios_runtime", status: "ready" }] },
    { platform: "android", status: "missing", running: null, checks: [{ name: "android_avd", status: "missing" }] },
    { platform: "web", status: "ready", running: null, checks: [{ name: "browser", status: "ready" }] },
    { platform: "docker", status: "error", running: false, checks: [{ name: "docker_engine", status: "error" }] },
  ],
};
const refreshToken = {};

beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.spyOn(dashboardApi, "getVisualEnvironment").mockResolvedValue(snapshot);
  localStorage.setItem("lumon.locale", "en");
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

it.each(["en", "zh-CN", "zh-TW"] as const)("separates prerequisites, running state and application proof (%s)", async (locale) => {
  localStorage.setItem("lumon.locale", locale);
  const element = document.createElement("div");
  const root = createRoot(element);
  try {
    await act(async () => root.render(<I18nProvider><VisualEnvironmentPanel workspaceId="one" refreshToken={refreshToken} /></I18nProvider>));
    expect(element.querySelectorAll(".visual-environment-item")).toHaveLength(4);
    expect(element.textContent).toContain(translate(locale, "environment.applicationUnverified"));
    expect(element.querySelector(".visual-environment-item")?.textContent).toContain(translate(locale, "environment.idle"));
    expect(dashboardApi.getVisualEnvironment).toHaveBeenCalledWith("one", false);
    expect(document.querySelectorAll('[role="tooltip"]:not([hidden])')).toHaveLength(0);
    const androidHelp = element.querySelector<HTMLButtonElement>('[aria-controls="environment-android-help"]')!;
    await act(async () => androidHelp.click());
    expect(document.querySelector('#environment-android-help:not([hidden])')?.textContent).toContain("AVD / System image");
    await act(async () => element.querySelector<HTMLButtonElement>(".panel-heading > button")!.click());
    expect(dashboardApi.getVisualEnvironment).toHaveBeenLastCalledWith("one", true);
  } finally { await act(async () => root.unmount()); }
});

it("drops old workspace responses and hides raw failure details", async () => {
  let resolveOld!: (value: VisualEnvironmentSnapshot) => void;
  vi.mocked(dashboardApi.getVisualEnvironment).mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve; }))
    .mockRejectedValueOnce(new Error("private credential"));
  const element = document.createElement("div");
  const root = createRoot(element);
  try {
    await act(async () => root.render(<I18nProvider><VisualEnvironmentPanel workspaceId="one" refreshToken={refreshToken} /></I18nProvider>));
    await act(async () => root.render(<I18nProvider><VisualEnvironmentPanel workspaceId="two" refreshToken={refreshToken} /></I18nProvider>));
    await act(async () => resolveOld(snapshot));
    expect(element.textContent).toContain("Environment check unavailable");
    expect(element.textContent).not.toContain("private credential");
    expect(element.querySelectorAll(".visual-environment-item")).toHaveLength(0);
  } finally { await act(async () => root.unmount()); }
});
