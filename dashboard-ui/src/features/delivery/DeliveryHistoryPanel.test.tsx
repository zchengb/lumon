import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { dashboardApi, ApiError } from "../../app/api";
import { I18nProvider, translate } from "../../shared/i18n";
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
    runs: [{ ...run, duration_seconds: 0 }], polls: [{ run_id: "poll-1", state: "running", phase: "discover", started_at: run.started_at, finished_at: null, detail: "Checking Stories.", duration_seconds: null }],
  };
  const fetch = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue(history);
  const events = vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([
    { at: run.started_at, phase: "verification", detail: "Version strings match. <script>not executable</script>" },
    { at: run.started_at, phase: "verification", detail: "command execution: completed (exit 0)", command: "git status --short; echo '<script>not executable</script>'", operation_id: "cmd-1", exit_code: 0 },
    { at: run.started_at, phase: "verification", detail: "command execution: started" },
  ]);
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  const onError = vi.fn();
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={onError} /></I18nProvider>));
    expect(fetch).toHaveBeenCalledWith("workspace-1");
    expect(events).toHaveBeenCalledWith("workspace-1", "story-1");
    expect(container.textContent).toContain("1m2s");
    expect(container.querySelectorAll(".delivery-stages .is-running")).toHaveLength(1);
    expect(container.querySelector(".delivery-stages .is-running .spin")).not.toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("1m3s");
    expect(fetch).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("1m4s");
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(container.querySelector(".delivery-progress-story")?.textContent).toBe(`${run.story_key}${run.story_title}`);
    expect(container.querySelector(".delivery-progress-story-title")?.textContent).toBe(run.story_title);
    expect(container.querySelector(".delivery-stages [aria-current=step]")?.textContent).not.toBeNull();
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(3);
    expect(container.querySelector(".delivery-activity-details")).not.toBeNull();
    expect(container.querySelector("script")).toBeNull();
    const commandDetails = container.querySelector<HTMLDetailsElement>(".delivery-command-details")!;
    expect(commandDetails.open).toBe(false);
    expect(commandDetails.querySelector("summary")?.textContent).toBe(translate(locale, "autoDelivery.commandDetails"));
    await act(async () => commandDetails.querySelector("summary")!.click());
    expect(commandDetails.open).toBe(true);
    expect(commandDetails.querySelector("code")?.textContent).toContain("git status --short");
    expect(commandDetails.querySelector("dl")?.textContent).toContain("cmd-1");
    expect(commandDetails.querySelector("dl")?.textContent).toContain("0");
    expect(container.textContent).toContain(translate(locale, "autoDelivery.commandUnavailable"));
    expect(container.querySelector("a")?.getAttribute("target")).toBe("_blank");
    expect(container.querySelector<HTMLButtonElement>(".delivery-history-delete")?.disabled).toBe(true);
    const completed = { ...run, state: "completed" as const, phase: "handoff", finished_at: "2026-10-07T08:12:13Z", duration_seconds: 733, verification_summary: "Seven version constants validated.", detail: "Local-only change; no deployment." };
    fetch.mockResolvedValue({ runs: [completed], polls: [{ ...history.polls[0]!, state: "completed", duration_seconds: 733, finished_at: completed.finished_at }] });
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.textContent).toContain("12m13s");
    expect(container.querySelector(".delivery-stages .is-running")).toBeNull();
    expect(vi.getTimerCount()).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("12m13s");
    const historyTable = container.querySelector<HTMLTableElement>(".delivery-history-table")!;
    expect(Array.from(historyTable.querySelectorAll("thead th"), (cell) => cell.textContent)).toEqual([
      translate(locale, "autoDelivery.story"), translate(locale, "autoScan.started"),
      translate(locale, "autoScan.status"), translate(locale, "autoScan.duration"),
      translate(locale, "autoDelivery.actions"),
    ]);
    const cells = historyTable.querySelectorAll("tbody td");
    expect(cells).toHaveLength(5);
    expect(cells[0]?.textContent).toContain(run.story_key);
    expect(cells[0]?.textContent).toContain(run.branch);
    expect(cells[0]?.querySelector(".delivery-story-line")?.textContent).toBe(`${run.story_key}${run.story_title}`);
    expect(cells[0]?.querySelector(".delivery-story-title")?.getAttribute("title")).toBe(run.story_title);
    expect(cells[4]?.querySelector(".delivery-history-delete")?.textContent).toBe(translate(locale, "autoDelivery.delete"));
    expect(cells[2]?.textContent).toBe(translate(locale, "autoDelivery.status.completed"));
    expect(cells[2]?.querySelector("small")).toBeNull();
    expect(cells[3]?.textContent).toBe("12m13s");
    expect(historyTable.textContent).not.toContain("Seven version constants validated.");
    expect(historyTable.textContent).not.toContain("Local-only change; no deployment.");
    const schedulerTable = container.querySelectorAll<HTMLTableElement>(".delivery-history-table")[1]!;
    expect(Array.from(schedulerTable.querySelectorAll("thead th"), (cell) => cell.textContent)).toEqual([
      translate(locale, "autoScan.started"), translate(locale, "autoScan.status"),
      translate(locale, "autoScan.duration"),
    ]);
    expect(schedulerTable.querySelectorAll("tbody td")).toHaveLength(3);
    expect(schedulerTable.querySelector("tbody td:last-child")?.textContent).toBe("12m13s");
    expect(schedulerTable.textContent).not.toContain("Checking Stories.");
    expect(schedulerTable.closest("section")?.querySelector(".panel-heading .muted")).toBeNull();
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(5);
    const inspect = container.querySelector<HTMLButtonElement>(".delivery-history-table .delivery-inspect")!;
    await act(async () => inspect.click());
    expect(events).toHaveBeenLastCalledWith("workspace-1", "story-1");
    fetch.mockResolvedValue({ runs: [], polls: [{ ...history.polls[0]!, state: "idle", phase: "implementation", detail: "AUTO_DELIVERY_IDLE", duration_seconds: 40 }] });
    const latest = container.querySelector<HTMLButtonElement>(".panel-actions .button")!;
    await act(async () => latest.click());
    expect(container.textContent).not.toContain("AUTO_DELIVERY_IDLE");
    expect(container.querySelector(".delivery-progress-story-title")).toBeNull();
    expect(historyTable.querySelector(".empty-table")?.getAttribute("colspan")).toBe("5");
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(1);
    await act(async () => schedulerTable.querySelector<HTMLButtonElement>(".delivery-inspect")!.click());
    expect(events).toHaveBeenLastCalledWith("workspace-1", "poll-1");
    expect(onError).not.toHaveBeenCalled();
  } finally {
    await act(async () => root.unmount());
    expect(vi.getTimerCount()).toBe(0);
    container.remove();
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers();
    localStorage.removeItem("lumon.locale");
  }
});

it.each(["failed", "blocked", "completed"] as const)("does not animate or advance a %s Story while its poll is still running", async (state) => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  const fetch = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({
    runs: [{ ...run, state, duration_seconds: 12 }],
    polls: [{ run_id: "poll-1", state: "running", phase: "discover", started_at: run.started_at, finished_at: null, detail: "Finishing poll", duration_seconds: null }],
  });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([]);
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    expect(container.querySelector(".delivery-stages .is-running")).toBeNull();
    expect(container.querySelector(".delivery-stages .spin")).toBeNull();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("0m12s");
    expect(fetch).toHaveBeenCalledTimes(1);
  } finally {
    await act(async () => root.unmount());
    expect(vi.getTimerCount()).toBe(0);
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

it.each([false, true])("confirms deleting a terminal row, persists refresh and clears its selection (accepted=%s)", async (accepted) => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  let saved: DeliveryHistory = { runs: [{ ...run, state: "completed", poll_id: null }], polls: [] };
  vi.spyOn(dashboardApi, "getDeliveryHistory").mockImplementation(async () => saved);
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([]);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(accepted);
  const remove = vi.spyOn(dashboardApi, "deleteDeliveryHistory").mockImplementation(async () => { saved = { runs: [], polls: [] }; });
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    await act(async () => container.querySelector<HTMLButtonElement>(".delivery-history-table .delivery-inspect")!.click());
    await act(async () => container.querySelector<HTMLButtonElement>(".delivery-history-delete")!.click());
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("MBPAS-1"));
    if (accepted) {
      expect(remove).toHaveBeenCalledExactlyOnceWith("workspace-1", "story-1");
      expect(container.querySelector(".delivery-history-delete")).toBeNull();
      expect(container.querySelector(".delivery-facts")).toBeNull();
      await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
      expect(container.querySelector(".delivery-history-delete")).toBeNull();
    } else {
      expect(remove).not.toHaveBeenCalled();
      expect(container.querySelector(".delivery-history-delete")).not.toBeNull();
    }
  } finally {
    await act(async () => root.unmount());
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

it("prevents duplicate deletes and retains a row when deletion fails", async () => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [{ ...run, state: "blocked", poll_id: null }], polls: [] });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([]);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  let reject: (reason: Error) => void = () => {};
  const remove = vi.spyOn(dashboardApi, "deleteDeliveryHistory").mockImplementation(() => new Promise((_resolve, fail) => { reject = fail; }));
  const onError = vi.fn();
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={onError} /></I18nProvider>));
    const button = container.querySelector<HTMLButtonElement>(".delivery-history-delete")!;
    await act(async () => button.click());
    expect(button.disabled).toBe(true);
    await act(async () => { button.click(); await vi.advanceTimersByTimeAsync(6000); });
    expect(remove).toHaveBeenCalledTimes(1);
    await act(async () => reject(new ApiError(409, "Delivery busy")));
    expect(onError).toHaveBeenLastCalledWith("Delivery busy");
    expect(container.querySelector(".delivery-story-title")?.textContent).toBe(run.story_title);
    expect(container.querySelector<HTMLButtonElement>(".delivery-history-delete")?.disabled).toBe(false);
  } finally {
    await act(async () => root.unmount());
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
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
    const emptyScheduler = container.querySelectorAll(".delivery-history-table")[1]!;
    expect(emptyScheduler.querySelector(".empty-table")?.getAttribute("colspan")).toBe("3");
    expect(onError).toHaveBeenCalledWith("Activity unavailable.");
    await act(async () => root.unmount());
    await vi.advanceTimersByTimeAsync(3000);
    expect(fetch).toHaveBeenCalledTimes(1);
  } finally {
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers();
    localStorage.removeItem("lumon.locale");
  }
});
