import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { dashboardApi, ApiError } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { DeliveryHistory, DeliveryRun } from "../../shared/types";
import { DeliveryHistoryPanel } from "./DeliveryHistoryPanel";

const run: DeliveryRun = {
  run_id: "story-1", story_key: "MBPAS-1", story_title: "Admin portal version bump",
  state: "running", phase: "verification", started_at: "2026-10-07T08:00:00Z",
  finished_at: null, jira_url: "https://inspire.atlassian.net/browse/MBPAS-1",
  repository: "digital-platform-admin", branch: "codex/version-test", pull_request_url: null,
  verification_summary: null, detail: "Checking the version constants.", reason: null,
  poll_id: "poll-1", duration_seconds: null,
};

it.each(["en", "zh-CN", "zh-TW"] as const)("refreshes live progress and inspects history in %s", async (locale) => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-07T08:01:02Z"));
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", locale);
  const history: DeliveryHistory = {
    runs: [run], polls: [{ run_id: "poll-1", state: "running", phase: "discover", started_at: run.started_at, finished_at: null, detail: "Checking Stories.", duration_seconds: null }],
  };
  const fetch = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue(history);
  const events = vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([{ at: run.started_at, phase: "verification", detail: "Version strings match. <script>not executable</script>" }]);
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onError = vi.fn();
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={onError} /></I18nProvider>));
    expect(fetch).toHaveBeenCalledWith("workspace-1");
    expect(events).toHaveBeenCalledWith("workspace-1", "story-1");
    expect(container.textContent).toContain("1m2s");
    expect(container.querySelector(".delivery-stages [aria-current=step]")?.textContent).not.toBeNull();
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(3);
    expect(container.querySelector(".delivery-activity-details")).not.toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("a")?.getAttribute("target")).toBe("_blank");
    const completed = { ...run, state: "completed" as const, phase: "handoff", finished_at: "2026-10-07T08:12:13Z", duration_seconds: 733, verification_summary: "Seven version constants validated.", detail: "Local-only change; no deployment." };
    fetch.mockResolvedValue({ runs: [completed], polls: [{ ...history.polls[0]!, state: "completed", duration_seconds: 733, finished_at: completed.finished_at }] });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(container.textContent).toContain("12m13s");
    expect(container.textContent).toContain("Seven version constants validated.");
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(5);
    const inspect = container.querySelector<HTMLButtonElement>(".delivery-history-table .delivery-inspect")!;
    await act(async () => inspect.click());
    expect(events).toHaveBeenLastCalledWith("workspace-1", "story-1");
    fetch.mockResolvedValue({ runs: [], polls: [{ ...history.polls[0]!, state: "idle", phase: "implementation", detail: "AUTO_DELIVERY_IDLE", duration_seconds: 40 }] });
    const latest = container.querySelector<HTMLButtonElement>(".panel-actions .button")!;
    await act(async () => latest.click());
    expect(container.textContent).not.toContain("AUTO_DELIVERY_IDLE");
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(1);
    expect(onError).not.toHaveBeenCalled();
  } finally {
    await act(async () => root.unmount());
    container.remove();
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers();
    localStorage.removeItem("lumon.locale");
  }
});

it("keeps run history visible if the activity request fails and cancels refresh on unmount", async () => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  const fetch = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [{ ...run, poll_id: null }], polls: [] });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockRejectedValue(new ApiError(409, "Activity unavailable."));
  const onError = vi.fn();
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={onError} /></I18nProvider>));
    expect(container.textContent).toContain("Admin portal version bump");
    expect(onError).toHaveBeenCalledWith("Activity unavailable.");
    await act(async () => root.unmount());
    await vi.advanceTimersByTimeAsync(3000);
    expect(fetch).toHaveBeenCalledTimes(1);
  } finally {
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers();
    localStorage.removeItem("lumon.locale");
  }
});
