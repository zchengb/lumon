import { act } from "react";
import { createRoot } from "react-dom/client";
import { expect, it, vi } from "vitest";
import { dashboardApi } from "../../app/api";
import { I18nProvider } from "../../shared/i18n";
import type { ScanFinding, ScanRun, WorkspaceSettings } from "../../shared/types";
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
  const settings: WorkspaceSettings = {
    workspace_id: "workspace-id",
    feishu_webhook: { enabled: false, configured: false, masked_url: null },
    auto_delivery: { enabled: false, trigger_hooks: [], schedule_expression: "" },
    auto_scan: { enabled: false, trigger_hooks: [], schedule_expression: "", lookback_days: 7, workflow_description: "" },
  };
  const container = document.createElement("div");
  const root = createRoot(container);
  const listScans = vi.spyOn(dashboardApi, "listScans").mockResolvedValue(runs);
  try {
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    localStorage.setItem("lumon.locale", locale);
    await act(async () => root.render(<I18nProvider><AutoScanPage
      workspaceId={settings.workspace_id}
      settings={settings}
      onSave={async () => true}
      onDirtyChange={vi.fn()}
      onError={vi.fn()}
    /></I18nProvider>));
    const cells = container.querySelectorAll(".scan-history-table tbody td:nth-child(4)");
    expect(Array.from(cells, (cell) => cell.textContent)).toEqual(
      durations.map(([, label]) => label),
    );
    const history = container.querySelector(".scan-history-panel");
    expect(history?.querySelectorAll("h2")).toHaveLength(1);
    expect(history?.querySelector("h2")?.textContent).toBe("Scan history");
    expect(history?.querySelector(".eyebrow")).toBeNull();
    expect(history?.querySelector(".settings-description")).toBeNull();
    const findingCells = container.querySelectorAll(".scan-history-table tbody td:nth-child(3)");
    const labels = locale === "en" ? ["High", "Medium", "Low"] : ["高", "中", "低"];
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
  } finally {
    await act(async () => root.unmount());
    listScans.mockRestore();
    vi.unstubAllGlobals();
    localStorage.removeItem("lumon.locale");
  }
});
