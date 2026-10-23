import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { ScanFinding, ScanRun } from "../../shared/types";
import { AutoScanPage } from "./AutoScanPage";

it.each(["en", "zh-CN", "zh-TW"] as const)("shows compact scan history with severity counts and readable durations in %s", async (locale) => {
  const durations: Array<[number | null, string]> = [
    [null, "—"],
    [0, "0m0s"],
    [59, "0m59s"],
    [60, "1m0s"],
    [733, "12m13s"],
    [934, "15m34s"],
    [528, "8m48s"],
    [1218, "20m18s"],
    [3600, "60m0s"],
    [7200, "120m0s"],
    [9000, "150m0s"],
  ];
  const runs = durations.map(([seconds], index): ScanRun => ({
    run_id: `scan-${index}`,
    state: seconds === null ? "running" : "completed",
    phase: seconds === null ? "review" : "completed",
    started_at: "2026-09-30T04:00:00Z",
    finished_at: seconds === null ? null : "2026-09-30T05:00:00Z",
    lookback_days: 7,
    repositories_scanned: 0,
    repositories_failed: 0,
    findings: [],
    failures: [],
    hook_results: [],
    html_available: false,
    pdf_available: false,
    duration_seconds: seconds,
  }));
  const interruptionReason = "Auto Scan was interrupted before completion.";
  runs[0] = { ...runs[0], state: "failed", failures: [interruptionReason] };
  const findings = ["Low", "High", "Medium", "High"].map((severity, index): ScanFinding => ({
    title: `Finding ${index}`,
    severity,
    repository: "example",
    impact: "",
    trigger: "",
    file: "",
    line_range: "",
    code_snippet: "",
    suggestion: "",
    root_cause: "",
    validation: "",
    issue_id: `issue-${index}`,
    issue_status: "open",
    pr_url: null,
  }));
  runs[1] = { ...runs[1], state: "completed_with_findings", findings, html_available: true, pdf_available: true };
  runs[2] = { ...runs[2], state: "completed_with_findings", findings: findings.filter((finding) => finding.severity === "High") };
  runs[10] = { ...runs[10], findings: [{ ...findings[0], issue_id: "old-only", title: "Finding from oldest scan" }] };
  const container = document.createElement("div");
  const root = createRoot(container);
  const listScans = vi.spyOn(dashboardApi, "listScans").mockResolvedValue(runs);
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", locale);
    await act(async () => root.render(<I18nProvider><AutoScanPage
      workspaceId="workspace-id"
      onError={vi.fn()}
    /></I18nProvider>));
    const cells = container.querySelectorAll(".scan-history-table tbody td:nth-child(4)");
    expect(Array.from(cells, (cell) => cell.textContent)).toEqual(
      durations.slice(0, 10).map(([, label]) => label),
    );
    expect(container.querySelector(".settings-panel")).toBeNull();
    expect(container.querySelector(".page-heading")?.textContent).toBe("Auto Scan");
    expect(container.querySelector(".page-heading p")).toBeNull();
    expect(container.querySelector("#auto-scan-description")).toBeNull();
    expect(container.querySelector("#auto-scan-hooks")).toBeNull();
    expect(container.querySelector('[role="switch"]')).toBeNull();
    const history = container.querySelector(".scan-history-panel");
    const scrollRegion = history?.querySelector(".scan-history-scroll");
    expect(scrollRegion?.getAttribute("tabindex")).toBe("0");
    expect(scrollRegion?.getAttribute("role")).toBe("region");
    expect(scrollRegion?.getAttribute("aria-label")).toBe("Scan history");
    const interruptedStatus = history?.querySelector("tbody tr:first-child .status-pill");
    expect(interruptedStatus?.classList.contains("status-danger")).toBe(true);
    expect(interruptedStatus?.getAttribute("title")).toBe(interruptionReason);
    expect(history?.querySelectorAll("h2")).toHaveLength(1);
    expect(history?.querySelector("h2")?.textContent).toBe("Scan history");
    expect(history?.querySelector(".eyebrow")).toBeNull();
    expect(history?.querySelector(".settings-description")).toBeNull();
    const findingCells = container.querySelectorAll(".scan-history-table tbody td:nth-child(3)");
    const labels = ["High", "Medium", "Low"];
    expect(Array.from(findingCells[1].querySelectorAll(".scan-severity"), (badge) => badge.textContent)).toEqual(
      [`${labels[0]}: 2`, `${labels[1]}: 1`, `${labels[2]}: 1`],
    );
    expect(findingCells[2].textContent).toBe(`${labels[0]}: 2`);
    expect(findingCells[0].textContent).toBe("—");
    expect(findingCells[3].textContent).toBe("—");
    const links = container.querySelectorAll<HTMLAnchorElement>(".scan-artifacts a");
    expect(Array.from(links, (link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["HTML", "/api/workspaces/workspace-id/scans/scan-1/artifacts/html"],
      ["PDF", "/api/workspaces/workspace-id/scans/scan-1/artifacts/pdf"],
    ]);
    expect(links[0].target).toBe("_blank");
    expect(links[0].rel).toContain("noreferrer");
    expect(links[0].hasAttribute("download")).toBe(false);
    const issues = container.querySelector(".scan-findings-panel");
    expect(issues?.textContent).toContain("Finding from oldest scan");
    expect(issues?.querySelectorAll("article")).toHaveLength(5);
    await act(async () => container.querySelector<HTMLButtonElement>(".scan-history-pagination button:last-child")!.click());
    expect(container.querySelectorAll(".scan-history-table tbody tr")).toHaveLength(1);
    expect(issues?.querySelectorAll("article")).toHaveLength(5);
  } finally {
    await act(async () => root.unmount());
    listScans.mockRestore();
    vi.unstubAllGlobals();
    localStorage.removeItem("lumon.locale");
  }
});

it("shows unavailable issues rather than an empty result when history loading fails", async () => {
  const container = document.createElement("div");
  const root = createRoot(container);
  const onError = vi.fn();
  const listScans = vi.spyOn(dashboardApi, "listScans").mockRejectedValue(new Error("private response"));
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", "en");
    await act(async () => root.render(<I18nProvider><AutoScanPage workspaceId="workspace-id" onError={onError} /></I18nProvider>));
    const issues = container.querySelector(".scan-findings-panel");
    expect(issues?.textContent).toContain("Issues could not be loaded");
    expect(issues?.textContent).not.toContain("No issues match");
    expect(container.textContent).not.toContain("private response");
    expect(onError).toHaveBeenCalled();
  } finally {
    await act(async () => root.unmount());
    listScans.mockRestore();
    vi.unstubAllGlobals();
    localStorage.removeItem("lumon.locale");
  }
});

it("persists an ignore choice and replaces the displayed history with the server response", async () => {
  const finding: ScanFinding = {
    title: "Unnecessary issue", severity: "Medium", repository: "app", impact: "Impact", trigger: "", file: "", line_range: "", code_snippet: "", suggestion: "", root_cause: "", validation: "", issue_id: "one", issue_status: "open", pr_url: null,
  };
  const run: ScanRun = {
    run_id: "scan-1", state: "completed_with_findings", phase: "completed", started_at: "2026-10-22T00:00:00Z", finished_at: null, lookback_days: 7, repositories_scanned: 1, repositories_failed: 0, findings: [finding], failures: [], hook_results: [], html_available: false, pdf_available: false, duration_seconds: 10,
  };
  const list = vi.spyOn(dashboardApi, "listScans").mockResolvedValue([run]);
  const ignore = vi.spyOn(dashboardApi, "ignoreScanFinding").mockResolvedValue([{ ...run, findings: [{ ...finding, issue_status: "ignored" }] }]);
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", "en");
    await act(async () => root.render(<I18nProvider><AutoScanPage workspaceId="workspace-id" onError={vi.fn()} /></I18nProvider>));
    await act(async () => container.querySelector<HTMLButtonElement>(".scan-finding-ignore")!.click());
    expect(ignore).toHaveBeenCalledExactlyOnceWith("workspace-id", "scan-1", 0);
    expect(container.querySelector(".scan-finding .status-pill")?.textContent).toBe("Ignored");
    expect(container.querySelector(".scan-finding-ignore")).toBeNull();
  } finally {
    await act(async () => root.unmount());
    list.mockRestore(); ignore.mockRestore(); confirm.mockRestore();
    vi.unstubAllGlobals(); localStorage.removeItem("lumon.locale");
  }
});
