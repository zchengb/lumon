import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { I18nProvider, translate } from "../../shared/i18n";
import type { ScanRun } from "../../shared/types";
import { ScanProgressPanel } from "./ScanProgressPanel";

const active: ScanRun = {
  run_id: "active", state: "running", phase: "review", started_at: "2026-10-24T00:00:00Z",
  finished_at: null, lookback_days: 7, repositories_scanned: 0, repositories_failed: 0,
  findings: [], failures: [], hook_results: [], html_available: false, pdf_available: false,
  duration_seconds: null,
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-24T00:00:10Z"));
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
});

afterEach(() => {
  vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
});

it.each(["en", "zh-CN", "zh-TW"] as const)("tracks real phases and ticks elapsed time in %s", async (locale) => {
  localStorage.setItem("lumon.locale", locale);
  const container = document.createElement("div");
  const root = createRoot(container);
  async function render(run: ScanRun): Promise<void> {
    await act(async () => root.render(<I18nProvider><ScanProgressPanel run={run} loading={false} unavailable={false} onRefresh={vi.fn()} /></I18nProvider>));
  }
  try {
    await render(active);
    expect(container.querySelectorAll(".scan-stages li")).toHaveLength(3);
    expect(container.querySelectorAll(".is-running")).toHaveLength(1);
    expect(container.querySelector("[aria-current=step]")?.textContent).toContain(translate(locale, "autoScan.stage.review"));
    expect(container.querySelector(".is-running .spin")).not.toBeNull();
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("0m10s");
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("0m11s");
    await render({ ...active, phase: "report" });
    expect(container.querySelectorAll(".is-complete")).toHaveLength(1);
    expect(container.querySelector("[aria-current=step]")?.textContent).toContain(translate(locale, "autoScan.stage.report"));
    await render({ ...active, phase: "hooks" });
    expect(container.querySelectorAll(".is-complete")).toHaveLength(2);
    expect(container.querySelector("[aria-current=step]")?.textContent).toContain(translate(locale, "autoScan.stage.hooks"));
    await render({ ...active, phase: "completed", state: "completed", duration_seconds: 75 });
    expect(container.querySelectorAll(".is-complete")).toHaveLength(3);
    expect(container.querySelector(".is-running, [aria-current=step]")).toBeNull();
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("1m15s");
    expect(vi.getTimerCount()).toBe(0);
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("1m15s");
  } finally {
    await act(async () => root.unmount());
    expect(vi.getTimerCount()).toBe(0);
  }
});

it.each([
  ["failed", "report", 1, "status-danger"],
  ["completed_with_failures", "completed", 2, "status-warning"],
] as const)("keeps %s distinct from successful completion", async (state, phase, completed, tone) => {
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><ScanProgressPanel run={{ ...active, state, phase, failures: ["Review incomplete"], duration_seconds: 12 }} loading={false} unavailable={false} onRefresh={vi.fn()} /></I18nProvider>));
    expect(container.querySelectorAll(".is-complete")).toHaveLength(completed);
    expect(container.querySelector(".is-running, .spin")).toBeNull();
    expect(container.querySelector(`.status-pill.${tone}`)?.getAttribute("title")).toBe("Review incomplete");
    expect(vi.getTimerCount()).toBe(0);
  } finally {
    await act(async () => root.unmount());
  }
});

it("resumes the timer when a hidden page becomes visible and never fabricates unknown stage progress", async () => {
  const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><ScanProgressPanel run={{ ...active, phase: "future-phase" }} loading={false} unavailable={false} onRefresh={vi.fn()} /></I18nProvider>));
    expect(container.querySelector(".is-complete, .is-running")).toBeNull();
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("0m10s");
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("0m10s");
    visibility.mockReturnValue("visible");
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".scan-progress-duration")?.textContent).toBe("0m16s");
  } finally {
    await act(async () => root.unmount());
    expect(vi.getTimerCount()).toBe(0);
  }
});

it("distinguishes empty history, loading and unavailable progress", async () => {
  localStorage.setItem("lumon.locale", "en");
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    for (const [loading, unavailable, label] of [
      [false, false, "No scans yet."], [true, false, "Loading scan history"],
      [false, true, "Scan progress could not be loaded"],
    ] as const) {
      await act(async () => root.render(<I18nProvider><ScanProgressPanel run={null} loading={loading} unavailable={unavailable} onRefresh={vi.fn()} /></I18nProvider>));
      expect(container.textContent).toContain(label);
      expect(container.querySelector(".scan-stages")).toBeNull();
    }
  } finally {
    await act(async () => root.unmount());
  }
});
