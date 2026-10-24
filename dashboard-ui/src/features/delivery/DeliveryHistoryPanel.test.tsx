import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { dashboardApi, ApiError } from "../../app/api";
import { I18nProvider, translate } from "../../shared/i18n";
import type { DeliveryActivity, DeliveryHistory, DeliveryPoll, DeliveryRun } from "../../shared/types";
import { DeliveryHistoryPanel } from "./DeliveryHistoryPanel";

const run: DeliveryRun = {
  run_id: "story-1", story_key: "MBPAS-1", story_title: "Admin portal version bump",
  state: "running", phase: "verification", started_at: "2026-10-07T08:00:00Z",
  finished_at: null, jira_url: "https://inspire.atlassian.net/browse/MBPAS-1",
  repository: "digital-platform-admin", branch: "codex/version-test", pull_request_url: null,
  verification_summary: null, detail: "Checking the version constants.", reason: null,
  poll_id: "poll-1", duration_seconds: null,
};

it("continues a blocked delivery once, then requests a real stop and waits for acknowledgement", async () => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  const history = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [{ ...run, state: "blocked", attempt: 1 }], polls: [] });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([]);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const control = vi.spyOn(dashboardApi, "controlDelivery").mockResolvedValue({ accepted: true });
  const container = document.createElement("div"); const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    const button = () => Array.from(container.querySelectorAll<HTMLButtonElement>(".delivery-progress-panel button")).find((item) => /Continue|Stop/.test(item.textContent ?? ""))!;
    const historyActions = () => Array.from(container.querySelectorAll(".delivery-history-table tbody tr:first-child td:last-child button"), (item) => item.textContent);
    expect(button().textContent).toContain("Continue");
    expect(historyActions()).toEqual(["Continue", "Delete"]);
    history.mockResolvedValue({ runs: [{ ...run, attempt: 2, attempt_started_at: new Date().toISOString(), stopping: false }], polls: [] });
    await act(async () => button().click());
    expect(control).toHaveBeenCalledExactlyOnceWith("workspace-1", run.run_id, "resume", 1);
    expect(container.textContent).toContain("Attempt 2");
    expect(button().textContent).toContain("Stop");
    expect(historyActions()).toEqual(["Delete"]);
    history.mockResolvedValue({ runs: [{ ...run, attempt: 2, stopping: true }], polls: [] });
    await act(async () => button().click());
    expect(control).toHaveBeenLastCalledWith("workspace-1", run.run_id, "stop", 2);
    expect(button().textContent).toContain("Stopping…");
    expect(historyActions()).toEqual(["Delete"]);
    expect(button().disabled).toBe(true);
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("Running");
    history.mockResolvedValue({ runs: [{ ...run, state: "stopped", attempt: 2, stopping: null }], polls: [] });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("Stopped");
    expect(button().textContent).toContain("Continue");
    expect(historyActions()).toEqual(["Continue", "Delete"]);
  } finally {
    await act(async () => root.unmount());
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

it("does not offer stop for a legacy execution or resume for a completed delivery", async () => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  const history = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [run], polls: [] });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([]);
  const container = document.createElement("div"); const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    expect(Array.from(container.querySelectorAll("button")).some((item) => item.textContent === "Stop")).toBe(false);
    history.mockResolvedValue({ runs: [{ ...run, state: "completed" }], polls: [] });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(Array.from(container.querySelectorAll("button")).some((item) => item.textContent === "Continue")).toBe(false);
  } finally {
    await act(async () => root.unmount());
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

it("follows a verification/development loop live without restarting the run", async () => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  const returned: DeliveryActivity = { at: "2026-10-07T08:02:00Z", phase: "implementation", detail: "Fixing the verification finding." };
  const activity: DeliveryActivity[] = [{ ...returned, at: run.started_at, phase: "verification" }, returned];
  const history = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [{ ...run, phase: "implementation" }], polls: [] });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue(activity);
  const container = document.createElement("div"); const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    expect(container.querySelector(".delivery-stages .is-returned")?.textContent).toBe("Verify");
    expect(container.querySelector(".delivery-stages [aria-current=step]")?.textContent).toBe("Develop");
    expect(container.querySelector(".delivery-rework")?.textContent).toContain("Recorded rework cycles: 1");
    history.mockResolvedValue({ runs: [run], polls: [] });
    activity.push({ ...returned, at: "2026-10-07T08:03:00Z", phase: "verification" });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(container.querySelector(".delivery-stages .is-returned")).toBeNull();
    expect(container.querySelector(".delivery-rework [role=status]")?.textContent).toBe("Verifying again · round 2");
    await act(async () => container.querySelector<HTMLButtonElement>(".delivery-history-table .delivery-inspect")!.click());
    expect(container.querySelector(".delivery-inspection .delivery-rework")?.textContent).toContain("Recorded rework cycles: 1");
    expect(history).toHaveBeenCalledWith("workspace-1");
  } finally {
    await act(async () => root.unmount());
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

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
    expect(container.querySelector(".delivery-progress-story")?.textContent).toBe(`[${run.story_key}] ${run.story_title}`);
    expect(container.querySelector(".delivery-progress-story")?.getAttribute("title")).toBe(`[${run.story_key}] ${run.story_title}`);
    expect(container.querySelector("a.delivery-progress-story")?.getAttribute("href")).toBe(run.jira_url);
    expect(container.querySelector(".delivery-progress-story svg")).toBeNull();
    expect(container.querySelector(".delivery-stages [aria-current=step]")?.textContent).not.toBeNull();
    expect(container.querySelectorAll(".delivery-stages .is-complete").length).toBe(3);
    expect(container.querySelector(".delivery-activity-details")).not.toBeNull();
    expect(container.querySelector(".delivery-summary")).toBeNull();
    expect(container.querySelector(".delivery-progress-panel")?.textContent).not.toContain(run.detail);
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
    expect(container.querySelector(".delivery-progress-panel")?.textContent).not.toContain(completed.detail);
    expect(container.querySelector(".delivery-progress-panel .delivery-activity-details")).not.toBeNull();
    expect(vi.getTimerCount()).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(container.querySelector(".delivery-facts")?.textContent).toContain("12m13s");
    const historyTable = container.querySelector<HTMLTableElement>(".delivery-history-table")!;
    expect(historyTable.closest(".delivery-history-scroll")?.getAttribute("tabindex")).toBe("0");
    expect(Array.from(historyTable.querySelectorAll("thead th"), (cell) => cell.textContent)).toEqual([
      translate(locale, "autoDelivery.story"), translate(locale, "autoScan.started"),
      translate(locale, "autoScan.status"), translate(locale, "autoScan.duration"),
      translate(locale, "autoDelivery.actions"),
    ]);
    const cells = historyTable.querySelectorAll("tbody td");
    expect(cells).toHaveLength(5);
    expect(cells[0]?.textContent).toContain(run.story_key);
    expect(cells[0]?.querySelector(".delivery-story-metadata")?.textContent).toBe(run.story_key);
    expect(cells[0]?.textContent).not.toContain(run.branch);
    expect(cells[0]?.querySelector(".delivery-story-line")?.textContent).toBe(`[${run.story_key}] ${run.story_title}`);
    expect(cells[0]?.querySelector(".delivery-story-line")?.getAttribute("title")).toBe(`[${run.story_key}] ${run.story_title}`);
    const storyLink = cells[0]?.querySelector("a.delivery-story-line");
    expect(storyLink?.getAttribute("href")).toBe(run.jira_url);
    expect(storyLink?.getAttribute("target")).toBe("_blank");
    expect(storyLink?.getAttribute("rel")).toBe("noreferrer");
    expect(storyLink?.textContent).toBe(`[${run.story_key}] ${run.story_title}`);
    expect(storyLink?.querySelector("svg")).toBeNull();
    expect(cells[4]?.querySelector(".delivery-history-delete")?.textContent).toBe(translate(locale, "autoDelivery.delete"));
    expect(cells[2]?.textContent).toBe(translate(locale, "autoDelivery.status.completed"));
    expect(cells[2]?.querySelector("small")).toBeNull();
    expect(cells[3]?.textContent).toBe("12m13s");
    expect(historyTable.textContent).not.toContain("Seven version constants validated.");
    expect(historyTable.textContent).not.toContain("Local-only change; no deployment.");
    const schedulerTable = container.querySelectorAll<HTMLTableElement>(".delivery-history-table")[1]!;
    expect(schedulerTable.closest(".delivery-history-scroll")?.getAttribute("tabindex")).toBe("0");
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
    const refresh = container.querySelector<HTMLButtonElement>(".panel-actions .button")!;
    await act(async () => refresh.click());
    expect(container.textContent).not.toContain("AUTO_DELIVERY_IDLE");
    expect(container.querySelector(".delivery-progress-story")).toBeNull();
    expect(historyTable.querySelector(".empty-table")?.getAttribute("colspan")).toBe("5");
    expect(container.querySelector(".delivery-stages")).toBeNull();
    await act(async () => schedulerTable.querySelector<HTMLButtonElement>(".delivery-inspect")!.click());
    expect(events).toHaveBeenLastCalledWith("workspace-1", "poll-1");
    expect(container.querySelector(".delivery-progress-panel .delivery-facts")).toBeNull();
    expect(schedulerTable.closest("section")?.querySelector(".delivery-inspection")).not.toBeNull();
    expect(onError).not.toHaveBeenCalled();
  } finally {
    await act(async () => root.unmount());
    expect(vi.getTimerCount()).toBe(0);
    container.remove();
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers();
    localStorage.removeItem("lumon.locale");
  }
});

it("prioritizes the newest running Story and keeps history inspections out of Current progress", async () => {
  vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-07T08:10:00Z"));
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true); localStorage.setItem("lumon.locale", "en");
  const older = { ...run, run_id: "older", story_key: "MBPAS-OLD", story_title: "Historical delivery", state: "completed" as const };
  const newest = { ...run, run_id: "newest", story_key: "MBPAS-NEW", story_title: "Newer finished delivery", state: "completed" as const, started_at: "2026-10-07T08:09:00Z", duration_seconds: 30 };
  const active = { ...run, run_id: "active", story_key: "MBPAS-LIVE", story_title: "Actual running delivery", started_at: "2026-10-07T08:08:00Z" };
  const poll: DeliveryPoll = { run_id: "poll-new", state: "idle", phase: "discover", started_at: "2026-10-07T08:09:59Z", finished_at: "2026-10-07T08:10:00Z", detail: "No eligible Stories", duration_seconds: 1 };
  const fetch = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [older, newest, active, { ...active, run_id: "active-older", started_at: "2026-10-07T08:07:00Z" }], polls: [poll] });
  const events = vi.spyOn(dashboardApi, "getDeliveryActivity").mockImplementation(async (_workspace, id) => [{ at: run.started_at, phase: "verification", detail: `Activity for ${id}` }]);
  const container = document.createElement("div"); const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    const progress = container.querySelector(".delivery-progress-panel")!;
    expect(progress.textContent).toContain("Actual running delivery");
    expect(progress.textContent).not.toContain("No eligible Stories");
    expect(progress.textContent).toContain("Activity for active");
    expect(events).toHaveBeenCalledExactlyOnceWith("workspace-1", "active");
    expect(progress.querySelectorAll(".delivery-stages .is-running")).toHaveLength(1);
    await act(async () => container.querySelector<HTMLButtonElement>('[aria-label="Inspect run MBPAS-OLD"]')!.click());
    expect(progress.textContent).toContain("Actual running delivery");
    expect(progress.textContent).not.toContain("Activity for older");
    expect(container.querySelector(".delivery-inspection")?.textContent).toContain("Historical delivery");
    expect(container.querySelector(".delivery-inspection")?.textContent).toContain("Activity for older");
    const scheduler = container.querySelectorAll(".delivery-history-table")[1]!.closest("section")!;
    await act(async () => scheduler.querySelector<HTMLButtonElement>(".delivery-inspect")!.click());
    expect(progress.textContent).toContain("Actual running delivery");
    expect(progress.textContent).not.toContain("Activity for poll-new");
    expect(scheduler.querySelector(".delivery-inspection")?.textContent).toContain("Activity for poll-new");
    await act(async () => scheduler.querySelector<HTMLButtonElement>(".delivery-inspection button")!.click());
    expect(container.querySelector(".delivery-inspection")).toBeNull();
    fetch.mockResolvedValue({ runs: [older, newest], polls: [poll] });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(progress.textContent).toContain("Newer finished delivery");
    expect(progress.textContent).not.toContain("Actual running delivery");
    expect(progress.querySelector(".is-running")).toBeNull();
    expect(progress.querySelectorAll(".delivery-stages .is-complete")).toHaveLength(5);
    fetch.mockResolvedValue({ runs: [older, newest, active], polls: [poll] });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(progress.textContent).toContain("Actual running delivery");
    expect(progress.querySelectorAll(".delivery-stages .is-running")).toHaveLength(1);
    fetch.mockResolvedValue({ runs: [{ ...older, attempt: 2, attempt_started_at: "2026-10-07T08:11:00Z" }, newest], polls: [poll] });
    await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
    expect(progress.textContent).toContain("Historical delivery");
    expect(progress.textContent).toContain("Attempt 2");
    expect(progress.textContent).not.toContain("Newer finished delivery");
  } finally {
    await act(async () => root.unmount()); await vi.advanceTimersByTimeAsync(0);
    expect(vi.getTimerCount()).toBe(0);
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

it.each(["idle", "running", "failed"] as const)("never shows a scheduler-only %s check in Current progress", async (state) => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true); localStorage.setItem("lumon.locale", "en");
  vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [], polls: [{ run_id: "poll-only", state, phase: "discover", started_at: run.started_at, finished_at: null, detail: "Scheduler-only evidence", duration_seconds: 2 }] });
  const events = vi.spyOn(dashboardApi, "getDeliveryActivity").mockResolvedValue([{ at: run.started_at, phase: "discover", detail: "Scheduler-only evidence" }]);
  const container = document.createElement("div"); const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={vi.fn()} /></I18nProvider>));
    const progress = container.querySelector(".delivery-progress-panel")!;
    expect(progress.querySelector(".delivery-stages, .delivery-facts")).toBeNull();
    expect(progress.textContent).toContain("No delivery runs yet");
    expect(events).not.toHaveBeenCalled();
    const scheduler = container.querySelectorAll(".delivery-history-table")[1]!.closest("section")!;
    await act(async () => scheduler.querySelector<HTMLButtonElement>(".delivery-inspect")!.click());
    expect(scheduler.querySelector(".delivery-inspection")?.textContent).toContain("Scheduler-only evidence");
    expect(progress.textContent).not.toContain("Scheduler-only evidence");
    expect(progress.querySelector(".delivery-stages")).toBeNull();
  } finally {
    await act(async () => root.unmount()); await vi.advanceTimersByTimeAsync(0);
    expect(vi.getTimerCount()).toBe(0);
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
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
    expect(container.querySelector(".delivery-story-line")?.textContent).toBe(`[${run.story_key}] ${run.story_title}`);
    expect(container.querySelector<HTMLButtonElement>(".delivery-history-delete")?.disabled).toBe(false);
  } finally {
    await act(async () => root.unmount());
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers(); localStorage.clear();
  }
});

it("keeps run history visible if the activity request fails and cancels refresh on unmount", async () => {
  vi.useFakeTimers(); vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  const fetch = vi.spyOn(dashboardApi, "getDeliveryHistory").mockResolvedValue({ runs: [{ ...run, poll_id: null, jira_url: null, branch: null }], polls: [] });
  vi.spyOn(dashboardApi, "getDeliveryActivity").mockRejectedValue(new ApiError(409, "Activity unavailable."));
  const onError = vi.fn();
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><DeliveryHistoryPanel workspaceId="workspace-1" onError={onError} /></I18nProvider>));
    expect(container.textContent).toContain("Admin portal version bump");
    expect(container.querySelector(".delivery-story-line")?.textContent).toBe(`[${run.story_key}] ${run.story_title}`);
    expect(container.querySelector("a.delivery-story-line, a.delivery-progress-story")).toBeNull();
    expect(container.querySelector(".delivery-story-metadata")?.textContent).toBe(run.story_key);
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
