import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { I18nProvider, translate } from "../../shared/i18n";
import type { DeliveryActivity, DeliveryRun } from "../../shared/types";
import { DeliveryRework, deliveryReworks } from "./DeliveryRework";

const event = (phase: string, detail = phase): DeliveryActivity => ({ at: "2026-10-23T08:00:00Z", phase, detail });
const returned = event("implementation", "Fixing dialog spacing after verification.");
const run: DeliveryRun = {
  run_id: "delivery-TEST-1", story_key: "TEST-1", story_title: "Test rework",
  state: "running", phase: "implementation", started_at: returned.at, finished_at: null,
  jira_url: null, repository: null, branch: null, pull_request_url: null,
  verification_summary: null, detail: returned.detail, reason: null, poll_id: null,
  duration_seconds: null,
};

it("counts phase returns, ignoring command noise, repeated updates and unknown phases", () => {
  const secondReturn = event("implementation", "Fixing the second verification finding.");
  expect(deliveryReworks([
    event("implementation"), event("verification"),
    { ...event("implementation"), command: "check", exit_code: 1 },
    { ...event("implementation"), operation_id: "op-1" },
    { ...event("implementation"), exit_code: 0 },
    event("implementation", "command execution: started"), event("unknown"),
    returned, event("implementation"), event("verification"), secondReturn,
  ])).toEqual([returned, secondReturn]);
  expect(deliveryReworks([event("claim"), event("implementation"), event("verification"), event("handoff")])).toEqual([]);
  expect(deliveryReworks([returned])).toEqual([]);
  expect(deliveryReworks([])).toEqual([]);
});

it.each(["en", "zh-CN", "zh-TW"] as const)("renders rework, re-verification and terminal states in %s", async (locale) => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", locale);
  const container = document.createElement("div");
  const root = createRoot(container);
  const render = async (current: DeliveryRun, reworks: DeliveryActivity[]) => {
    await act(async () => root.render(<I18nProvider><DeliveryRework run={current} reworks={reworks} timeLabel={(at) => at} /></I18nProvider>));
  };
  try {
    await render(run, []);
    expect(container.querySelector(".delivery-rework")).toBeNull();
    await render(run, [returned]);
    expect(container.textContent).toContain(translate(locale, "autoDelivery.reworkCount", { count: 1 }));
    expect(container.querySelector('[role="status"]')?.textContent).toBe(translate(locale, "autoDelivery.reworking"));
    expect(container.querySelector(".delivery-rework-path .is-current")?.textContent).toBe(translate(locale, "autoDelivery.stage.implementation"));
    expect(container.querySelector(".delivery-rework-path .is-current .spin")).not.toBeNull();
    expect(container.querySelector<HTMLDetailsElement>("details")?.open).toBe(false);
    await act(async () => container.querySelector("summary")!.click());
    expect(container.querySelector<HTMLDetailsElement>("details")?.open).toBe(true);
    expect(container.querySelector("time")?.dateTime).toBe(returned.at);
    expect(container.querySelector("details p")?.textContent).toBe(returned.detail);
    await render({ ...run, phase: "verification" }, [returned, returned]);
    expect(container.querySelector('[role="status"]')?.textContent).toBe(translate(locale, "autoDelivery.verificationRound", { round: 3 }));
    expect(container.querySelector(".delivery-rework-path .is-current")?.textContent).toBe(translate(locale, "autoDelivery.verifyAgain"));
    for (const state of ["failed", "blocked", "completed"] as const) {
      await render({ ...run, phase: "verification", state }, [returned]);
      expect(container.querySelector(".spin, [role=status], .is-current")).toBeNull();
      expect(container.querySelectorAll(".delivery-rework-path .is-complete")).toHaveLength(state === "completed" ? 2 : 1);
      expect(container.querySelectorAll(".delivery-rework-path .is-stopped")).toHaveLength(state === "completed" ? 0 : 1);
    }
  } finally {
    await act(async () => root.unmount());
    localStorage.clear(); vi.unstubAllGlobals();
  }
});
