import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { I18nProvider, translate } from "../../shared/i18n";
import type { ScanFinding, ScanRun } from "../../shared/types";
import { ScanFindingsPanel } from "./ScanFindingsPanel";
import { ApiError } from "../../app/api";

const finding: ScanFinding = {
  title: "Payment retry loses its reference", severity: "High", repository: "payments",
  impact: "A retry may charge twice.", trigger: "Retry after a timeout.", file: "src/payment.ts", line_range: "12-18",
  code_snippet: "<script>not executed</script>", suggestion: "Reuse the reference.", root_cause: "A new reference is generated.",
  validation: "Review only; not executed.", issue_id: "ISSUE-1", issue_status: "open", pr_url: "https://example.com/pull/1",
};
function run(run_id: string, started_at: string, findings: ScanFinding[]): ScanRun {
  return {
    run_id, started_at, findings, state: "completed_with_findings", phase: "completed", finished_at: started_at,
    lookback_days: 7, repositories_scanned: 1, repositories_failed: 0, failures: [], hook_results: [],
    html_available: false, pdf_available: false, duration_seconds: 0,
  };
}

beforeEach(() => { vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true); localStorage.setItem("lumon.locale", "en"); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });

it("confirms ignores, submits the exact occurrence once and shows saved status", async () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  let finish: () => void = () => {};
  const onIgnore = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
  const runs = [run("scan-1", "2026-10-22T00:00:00Z", [{ ...finding, issue_status: "resolved" }, { ...finding, issue_id: "second" }])];
  const container = document.createElement("div");
  const root = createRoot(container);
  const render = () => <I18nProvider><ScanFindingsPanel runs={runs} loading={false} unavailable={false} onIgnore={onIgnore} /></I18nProvider>;
  try {
    await act(async () => root.render(render()));
    expect(container.querySelectorAll(".scan-finding-ignore")).toHaveLength(1);
    const button = container.querySelector<HTMLButtonElement>(".scan-finding-ignore")!;
    await act(async () => button.click());
    expect(onIgnore).not.toHaveBeenCalled();
    confirm.mockReturnValue(true);
    await act(async () => button.click());
    expect(button.disabled).toBe(true);
    expect(button.textContent).toBe("Ignoring…");
    await act(async () => button.click());
    expect(onIgnore).toHaveBeenCalledExactlyOnceWith("scan-1", 1);
    runs[0] = { ...runs[0], findings: runs[0].findings.map((item) => ({ ...item, issue_status: "ignored" })) };
    await act(async () => { finish(); });
    await act(async () => root.render(render()));
    expect(container.querySelectorAll(".scan-finding-ignore")).toHaveLength(0);
    expect(container.querySelectorAll("article")).toHaveLength(0);
    await act(async () => container.querySelectorAll<HTMLButtonElement>(".scan-finding-filters button")[3].click());
    expect(container.querySelectorAll(".scan-finding .status-pill")[1]?.textContent).toBe("Ignored");
  } finally { await act(async () => root.unmount()); }
});

it("keeps the issue visible and allows retry when saving fails", async () => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const onIgnore = vi.fn().mockRejectedValue(new ApiError(404, "private unavailable endpoint"));
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><ScanFindingsPanel runs={[run("one", "2026-10-22T00:00:00Z", [finding])]} loading={false} unavailable={false} onIgnore={onIgnore} /></I18nProvider>));
    await act(async () => container.querySelector<HTMLButtonElement>(".scan-finding-ignore")!.click());
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Could not ignore this issue");
    expect(container.textContent).not.toContain("private unavailable endpoint");
    expect(container.querySelector(".scan-finding .status-pill")?.textContent).toBe("Open");
    expect(container.querySelector<HTMLButtonElement>(".scan-finding-ignore")?.disabled).toBe(false);
  } finally { await act(async () => root.unmount()); }
});

it.each(["en", "zh-CN", "zh-TW"] as const)("shows every recorded issue with details and status filters in %s", async (locale) => {
  localStorage.setItem("lumon.locale", locale);
  const runs = [run("latest", "2026-10-22T12:00:00Z", [
    finding,
    { ...finding, issue_id: "resolved", issue_status: "resolved", title: "Resolved finding" },
    { ...finding, issue_id: "ignored", issue_status: " IGNORE ", title: "Ignored finding" },
    { ...finding, issue_id: "in-progress", issue_status: "in_progress" },
    { ...finding, issue_id: "pr-open", issue_status: "pr_open" },
    { ...finding, issue_id: "reopened", issue_status: "reopened" },
  ])];
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><ScanFindingsPanel runs={runs} loading={false} unavailable={false} /></I18nProvider>));
    expect(container.querySelector("h2")?.textContent).toBe(translate(locale, "autoScan.issuesTitle"));
    expect(container.querySelector(".scan-findings-note")).toBeNull();
    expect(container.textContent).not.toContain(translate(locale, "autoScan.issuesDescription"));
    expect(container.querySelectorAll("article")).toHaveLength(4);
    expect(container.querySelector('.scan-finding-filters button[aria-pressed="true"]')?.textContent).toBe(`${translate(locale, "autoScan.open")} 4`);
    expect(container.textContent).not.toContain("Resolved finding");
    expect(container.textContent).not.toContain("Ignored finding");
    expect(container.querySelector(".scan-severity")?.textContent).toBe("High");
    const title = container.querySelector(".scan-finding h3")!;
    const tags = title.nextElementSibling;
    expect(tags?.classList.contains("scan-finding-tags")).toBe(true);
    expect(tags?.querySelectorAll(".scan-finding-tag")).toHaveLength(2);
    expect(tags?.querySelector(".status-pill")?.textContent).toBe(translate(locale, "autoScan.open"));
    const detail = container.querySelector("details");
    expect(detail?.open).toBe(false);
    await act(async () => { detail!.open = true; detail!.dispatchEvent(new Event("toggle")); });
    for (const value of [finding.impact, finding.trigger, finding.root_cause, finding.code_snippet, finding.suggestion, finding.validation, "src/payment.ts:12-18", "latest"]) {
      expect(detail?.textContent).toContain(value);
    }
    expect(detail?.querySelector("script")).toBeNull();
    const link = container.querySelector("a");
    expect(link?.getAttribute("href")).toBe(finding.pr_url);
    expect(link?.getAttribute("rel")).toContain("noopener");
    const filters = container.querySelectorAll<HTMLButtonElement>(".scan-finding-filters button");
    for (const [index, count] of [6, 4, 1, 1].entries()) {
      await act(async () => filters[index].click());
      expect(container.querySelectorAll("article")).toHaveLength(count);
      expect(filters[index].getAttribute("aria-pressed")).toBe("true");
    }
  } finally { await act(async () => root.unmount()); }
});

it("keeps the newest state per repository and ID without dropping other or untracked issues", async () => {
  const runs = [
    run("old", "2026-10-01T00:00:00Z", [finding, { ...finding, issue_id: "old-only", title: "Older unique issue" }]),
    run("new", "2026-10-22T00:00:00Z", [
      { ...finding, title: "Latest resolved issue", issue_status: "resolved" },
      { ...finding, repository: "different-repo" },
      { ...finding, issue_id: "untracked", title: "Untracked A" },
      { ...finding, issue_id: "untracked", title: "Untracked B" },
    ]),
  ];
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><ScanFindingsPanel runs={runs} loading={false} unavailable={false} /></I18nProvider>));
    expect(container.querySelectorAll("article")).toHaveLength(4);
    expect(container.textContent).not.toContain("Latest resolved issue");
    await act(async () => container.querySelectorAll<HTMLButtonElement>(".scan-finding-filters button")[0].click());
    expect(container.querySelectorAll("article")).toHaveLength(5);
    expect(container.querySelector("article h3")?.textContent).toBe("Latest resolved issue");
    expect(container.textContent).toContain("Older unique issue");
    expect(container.textContent).toContain("Untracked A");
    expect(container.textContent).toContain("Untracked B");
    await act(async () => container.querySelectorAll<HTMLButtonElement>(".scan-finding-filters button")[2].click());
    expect(container.querySelectorAll("article")).toHaveLength(1);
    expect(container.querySelector("article")?.textContent).toContain("new");
  } finally { await act(async () => root.unmount()); }
});

it("distinguishes loading, unavailable and empty results", async () => {
  const container = document.createElement("div");
  const root = createRoot(container);
  const render = (loading: boolean, unavailable: boolean) => <I18nProvider><ScanFindingsPanel runs={[]} loading={loading} unavailable={unavailable} /></I18nProvider>;
  try {
    await act(async () => root.render(render(true, false)));
    expect(container.textContent).toContain("Loading scan history");
    expect(container.textContent).not.toContain("No issues match");
    await act(async () => root.render(render(false, true)));
    expect(container.textContent).toContain("Issues could not be loaded");
    expect(container.textContent).not.toContain("No issues match");
    await act(async () => root.render(render(false, false)));
    expect(container.textContent).toContain("No issues match this status.");
  } finally { await act(async () => root.unmount()); }
});

it.each(["javascript:alert(1)", "data:text/html,bad", "https://user:secret@example.com", "not-a-url"])("does not link unsafe PR URLs: %s", async (pr_url) => {
  const container = document.createElement("div");
  const root = createRoot(container);
  try {
    await act(async () => root.render(<I18nProvider><ScanFindingsPanel runs={[run("one", "2026-10-22T00:00:00Z", [{ ...finding, pr_url }])]} loading={false} unavailable={false} /></I18nProvider>));
    expect(container.querySelector("a")).toBeNull();
  } finally { await act(async () => root.unmount()); }
});
