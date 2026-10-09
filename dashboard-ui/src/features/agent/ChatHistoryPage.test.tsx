import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import { ApiError, dashboardApi } from "../../app/api";
import { I18nProvider, LanguagePicker } from "../../shared/i18n";
import type { ChatInteraction, ChatInteractionDetail, ChatInteractionPage } from "../../shared/types";
import { ChatHistoryPage } from "./ChatHistoryPage";

const direct: ChatInteraction = {
  run_id: "direct-run", chat_id: "direct-chat", chat_type: "p2p", sender_id: "ou_12345678901234567890abcd",
  chat_name: null, sender_name: "Xiaobin Zheng",
  started_at: "2026-09-30T04:00:00Z", input_preview: "Review the change",
  output_preview: "Done. ![image](https://example.com/private-image.png)", status: "succeeded", duration_seconds: 733,
  trace_url: null,
};
const group: ChatInteraction = {
  ...direct, run_id: "group-run", chat_id: "group-chat", chat_type: "group", sender_id: "user-two", chat_name: "MBPass Engineering", sender_name: null,
  output_preview: "", status: "running", duration_seconds: null,
};

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.removeItem("lumon.locale"); });

it("shows a compact table with source tags and keeps full messages unloaded by default", async () => {
  const list = vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [direct, group], total: 22 });
  const detail = vi.spyOn(dashboardApi, "getConversation");
  const container = document.createElement("div");
  const root = createRoot(container);
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  try {
    await act(async () => root.render(<I18nProvider><LanguagePicker /><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
    expect(list).toHaveBeenLastCalledWith("workspace-one", "all", "", 0);
    expect(container.querySelectorAll("table")).toHaveLength(1);
    expect(Array.from(container.querySelectorAll("th"), (cell) => cell.textContent)).toEqual(["Started", "Source", "User", "Input", "Output", "Status", "Duration", "Langfuse"]);
    expect(container.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(container.textContent).toContain("12m13s");
    expect(container.textContent).toContain("ou_123…abcd");
    expect(container.textContent).toContain("MBPass Engineering");
    const directCells = container.querySelectorAll("tbody tr")[0].querySelectorAll("td");
    const groupSource = container.querySelectorAll("tbody tr")[1].querySelectorAll("td")[1];
    expect(directCells[1].textContent).toBe("Direct message");
    expect(directCells[1].querySelectorAll("[title], .chat-display-name, .chat-id")).toHaveLength(0);
    expect(groupSource.textContent).toBe("Group threadMBPass Engineering");
    expect(groupSource.querySelector(".chat-id")).toBeNull();
    expect(container.textContent).not.toContain(direct.chat_id);
    expect(container.textContent).not.toContain(group.chat_id);
    expect(directCells[2].textContent).toContain("Xiaobin Zheng");
    expect(directCells[2].querySelector(".chat-id")?.getAttribute("title")).toBe(direct.sender_id);
    expect(container.querySelectorAll("tbody tr")[1].lastElementChild?.textContent).toBe("—");
    expect(directCells[6].textContent).toBe("12m13s");
    expect(container.querySelectorAll("article, details, img, tbody a")).toHaveLength(0);
    expect(container.querySelector(".chat-source-direct")?.textContent).toBe("Direct message");
    expect(container.querySelector(".chat-source-group")?.textContent).toBe("Group thread");
    expect(container.querySelectorAll(".chat-message-toggle[aria-expanded=false]")).toHaveLength(3);
    expect(detail).not.toHaveBeenCalled();
    expect(container.querySelector("h1")?.textContent).toBe("Agent");
    const requestsBeforeLocaleChange = list.mock.calls.length;
    await act(async () => {
      const language = container.querySelector<HTMLSelectElement>(".language-picker select")!;
      language.value = "zh-TW";
      language.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(container.textContent).toContain("對話記錄");
    expect(list.mock.calls).toHaveLength(requestsBeforeLocaleChange);

    await act(async () => container.querySelectorAll<HTMLButtonElement>(".chat-pagination button")[1].click());
    expect(list).toHaveBeenLastCalledWith("workspace-one", "all", "", 20);
    list.mockResolvedValue({ items: [group], total: 1 });
    await act(async () => {
      const select = container.querySelector<HTMLSelectElement>("#chat-kind")!;
      select.value = "group";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });
    expect(list).toHaveBeenLastCalledWith("workspace-one", "group", "", 0);
    await act(async () => {
      const input = container.querySelector<HTMLInputElement>("#chat-search")!;
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, "user-two");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await act(async () => container.querySelector("form")?.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    expect(list).toHaveBeenLastCalledWith("workspace-one", "group", "user-two", 0);
  } finally {
    await act(async () => root.unmount());
  }
});

it.each([
  ["en", "View trace"], ["zh-CN", "查看链路"], ["zh-TW", "查看鏈路"],
])("links each recorded Langfuse trace in a new tab in %s", async (locale, label) => {
  const traceUrl = "https://jp.cloud.langfuse.com/project/project-one/traces/" + "a".repeat(32);
  const list = vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({
    items: [{ ...direct, status: "timed_out", trace_url: traceUrl }, group], total: 2,
  });
  const detail = vi.spyOn(dashboardApi, "getConversation");
  const container = document.createElement("div");
  const root = createRoot(container);
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", locale);
  try {
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
    const link = container.querySelector<HTMLAnchorElement>(".chat-trace-link")!;
    expect(link.textContent).toBe(label);
    expect(link.getAttribute("href")).toBe(traceUrl);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.getAttribute("aria-label")).toContain(label);
    expect(link.getAttribute("download")).toBeNull();
    expect(container.querySelectorAll("tbody tr")[1].lastElementChild?.textContent).toBe("—");
    expect(detail).not.toHaveBeenCalled();
    expect(list).toHaveBeenCalledTimes(1);
  } finally {
    await act(async () => root.unmount());
  }
});

it.each(["javascript:alert(1)", "https://user:secret@example.com/trace", "/private/trace"])(
  "does not render unsafe trace URL %s", async (traceUrl) => {
    vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [{ ...direct, trace_url: traceUrl }], total: 1 });
    const container = document.createElement("div");
    const root = createRoot(container);
    vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
    try {
      await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
      expect(container.querySelector(".chat-trace-link")).toBeNull();
      expect(container.querySelector("tbody tr")?.lastElementChild?.textContent).toBe("—");
    } finally {
      await act(async () => root.unmount());
    }
  },
);

it("expands input and Markdown output independently using one lazy, cached message read", async () => {
  vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [direct], total: 1 });
  let resolveDetail!: (detail: ChatInteractionDetail) => void;
  const detail = vi.spyOn(dashboardApi, "getConversation").mockReturnValue(new Promise((resolve) => { resolveDetail = resolve; }));
  const container = document.createElement("div");
  const root = createRoot(container);
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  try {
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
    await act(async () => container.querySelector<HTMLButtonElement>('[aria-label="Expand Output"]')!.click());
    expect(container.querySelector('[role="status"]')?.textContent).toBe("Loading full message…");
    expect(detail).toHaveBeenCalledExactlyOnceWith("workspace-one", direct.run_id);
    await act(async () => container.querySelector<HTMLButtonElement>('[aria-label="Expand Input"]')!.click());
    expect(detail).toHaveBeenCalledTimes(1);
    const input = "Original question\n".repeat(30) + "FULL INPUT END";
    const output = "**Complete**\n\n1. `Ready`\n2. FULL OUTPUT END\n\n![private](https://example.com/private.png)<script>alert(1)</script>";
    await act(async () => resolveDetail({ run_id: direct.run_id, input_text: input, output_text: output }));
    expect(container.querySelectorAll(".chat-message-expanded")).toHaveLength(2);
    expect(container.querySelector(".chat-input")?.textContent).toBe(input);
    expect(container.querySelector(".chat-output strong")?.textContent).toBe("Complete");
    expect(container.querySelector(".chat-output")?.textContent).toContain("FULL OUTPUT END");
    expect(container.querySelectorAll("img, script")).toHaveLength(0);
    const collapse = container.querySelector<HTMLButtonElement>('[aria-label="Collapse Output"]')!;
    expect(collapse.getAttribute("aria-controls")).toBe(container.querySelector(".chat-output")!.id);
    await act(async () => collapse.click());
    expect(container.querySelector(".chat-output")?.textContent).not.toContain("FULL OUTPUT END");
    expect(container.querySelector(".chat-input")?.textContent).toContain("FULL INPUT END");
    await act(async () => container.querySelector<HTMLButtonElement>('[aria-label="Expand Output"]')!.click());
    expect(detail).toHaveBeenCalledTimes(1);
    expect(container.querySelector(".chat-output")?.textContent).toContain("FULL OUTPUT END");
  } finally {
    await act(async () => root.unmount());
  }
});

it("keeps previews after a failed detail read and ignores details from a previous Workspace", async () => {
  vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [direct], total: 1 });
  let resolveDetail!: (detail: ChatInteractionDetail) => void;
  const detail = vi.spyOn(dashboardApi, "getConversation")
    .mockRejectedValueOnce(new ApiError(404, "Not found"))
    .mockReturnValueOnce(new Promise((resolve) => { resolveDetail = resolve; }));
  const container = document.createElement("div");
  const root = createRoot(container);
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  try {
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
    await act(async () => container.querySelector<HTMLButtonElement>('[aria-label="Expand Input"]')!.click());
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Could not load the message");
    expect(container.querySelector(".chat-input")?.textContent).toBe(direct.input_preview);
    await act(async () => container.querySelector<HTMLButtonElement>('[aria-label="Expand Output"]')!.click());
    expect(detail).toHaveBeenCalledTimes(2);
    expect(container.querySelectorAll(".chat-message-expanded")).toHaveLength(2);
    expect(container.querySelector('[role="alert"]')).toBeNull();
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-two" /></I18nProvider>));
    await act(async () => resolveDetail({ run_id: direct.run_id, input_text: "STALE PRIVATE INPUT", output_text: "STALE PRIVATE OUTPUT" }));
    expect(container.textContent).not.toContain("STALE PRIVATE");
    expect(container.querySelectorAll(".chat-message-expanded")).toHaveLength(0);
  } finally {
    await act(async () => root.unmount());
  }
});

it("renders compact Markdown outputs without executing HTML or loading remote images", async () => {
  const output = '**Result**: `Ready`\n\n1. First check\n2. Second check\n\n[Report](https://example.com/report) [unsafe](javascript:alert) [relative](/api/private) [credential](https://user:password@example.com)\n\n![private](https://example.com/image.png)\n<script>alert(1)</script>';
  vi.spyOn(dashboardApi, "listConversations").mockResolvedValue({ items: [{ ...direct, output_preview: output }], total: 1 });
  const container = document.createElement("div");
  const root = createRoot(container);
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  try {
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
    const cell = container.querySelector(".chat-output")!;
    expect(cell.querySelector("strong")?.textContent).toBe("Result");
    expect(cell.querySelector("code")?.textContent).toBe("Ready");
    expect(cell.querySelectorAll("ol li")).toHaveLength(2);
    expect(cell.querySelectorAll("a")).toHaveLength(1);
    expect(cell.querySelector("a")?.getAttribute("target")).toBe("_blank");
    expect(cell.querySelector("a")?.getAttribute("rel")).toBe("noopener noreferrer");
    expect(cell.querySelectorAll("script, img, iframe")).toHaveLength(0);
    expect(cell.textContent).not.toContain("**Result**");
  } finally {
    await act(async () => root.unmount());
  }
});

it("ignores stale Workspace results, clears old rows and handles empty or failed reads", async () => {
  let resolveFirst!: (value: ChatInteractionPage) => void;
  const first = new Promise<ChatInteractionPage>((resolve) => { resolveFirst = resolve; });
  const list = vi.spyOn(dashboardApi, "listConversations").mockImplementation(async (workspaceId) => (
    workspaceId === "workspace-one" ? first : { items: [group], total: 1 }
  ));
  const container = document.createElement("div");
  const root = createRoot(container);
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.setItem("lumon.locale", "en");
  try {
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-one" /></I18nProvider>));
    await act(async () => root.render(<I18nProvider><ChatHistoryPage workspaceId="workspace-two" /></I18nProvider>));
    await act(async () => resolveFirst({ items: [{ ...direct, input_preview: "STALE PRIVATE MESSAGE" }], total: 1 }));
    expect(container.textContent).toContain("MBPass Engineering");
    expect(container.textContent).not.toContain("STALE PRIVATE MESSAGE");
    list.mockRejectedValue(new ApiError(500, "Cannot read local Agent chat history."));
    await act(async () => container.querySelector<HTMLButtonElement>(".page-heading button")?.click());
    expect(container.querySelector("[role=alert]")?.textContent).toBe("Cannot read local Agent chat history.");
    expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
    list.mockResolvedValue({ items: [], total: 0 });
    await act(async () => container.querySelector<HTMLButtonElement>(".page-heading button")?.click());
    expect(container.textContent).toContain("No matching conversations.");
  } finally {
    await act(async () => root.unmount());
  }
});
