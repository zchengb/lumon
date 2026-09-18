import { act } from "react";
import { createRoot } from "react-dom/client";
import { Puzzle } from "lucide-react";
import { describe, expect, it, vi } from "vitest";
import {
  MarkdownDocumentsPage,
  type MarkdownDocumentApi,
  type MarkdownDocumentLabels,
  type MarkdownDocumentSummary,
} from "./MarkdownDocumentsPage";

interface TestSummary extends MarkdownDocumentSummary {
  id: string;
}

interface TestDocument extends TestSummary {
  content: string;
}

const labels: MarkdownDocumentLabels = {
  eyebrow: "Documents",
  title: "Documents",
  subtitle: "Manage documents.",
  unsaved: "Unsaved",
  select: "Select a document",
  refresh: "Refresh",
  new: "New document",
  empty: "No documents",
  emptyHelp: "Create one.",
  enabled: "Enabled",
  disabled: "Disabled",
  invalid: "Invalid",
  content: "Markdown",
  viewMode: "View mode",
  preview: "Preview",
  edit: "Edit",
  metadata: "Metadata",
  idHelp: "Create a draft.",
  enable: "Enable",
  disable: "Disable",
  save: "Save",
  delete: "Delete",
  saved: "Saved",
  created: "Created",
  deleted: "Deleted",
  confirmDelete: "Delete this document?",
  loadFailed: "Operation failed.",
  unsavedConfirm: "Discard changes?",
};

const starterContent = '---\nid = "my-capability"\n---\n\n# Draft';

function createDocumentApi(): MarkdownDocumentApi<TestSummary, TestDocument> {
  const document: TestDocument = {
    id: "my-capability",
    name: "My capability",
    enabled: true,
    brief: "Test capability.",
    path: "lumon/capabilities/my-capability.md",
    valid: true,
    error: null,
    content: starterContent,
  };
  return {
    list: vi.fn().mockResolvedValue([]),
    get: vi.fn().mockResolvedValue(document),
    create: vi.fn().mockResolvedValue(document),
    update: vi.fn().mockResolvedValue(document),
    delete: vi.fn().mockResolvedValue(undefined),
  };
}

function buttonWithText(container: HTMLElement, text: string): HTMLButtonElement {
  const button = Array.from(container.querySelectorAll("button")).find((item) =>
    item.textContent?.includes(text),
  );
  if (!(button instanceof HTMLButtonElement)) throw new Error(`Missing button: ${text}`);
  return button;
}

describe("MarkdownDocumentsPage", () => {
  it("keeps a new document local until the first save", async () => {
    const api = createDocumentApi();
    const container = document.createElement("div");
    const root = createRoot(container);

    try {
      await act(async () => {
        root.render(
          <MarkdownDocumentsPage
            workspaceId="workspace-1"
            onDirtyChange={vi.fn()}
            onNotice={vi.fn()}
            onError={vi.fn()}
            icon={Puzzle}
            labels={labels}
            starterContent={starterContent}
            api={api}
            getId={(item) => item.id}
          />,
        );
      });

      await act(async () => {
        buttonWithText(container, labels.new).click();
      });
      expect(api.create).not.toHaveBeenCalled();
      expect(container.querySelector("textarea")?.value).toBe(starterContent);

      await act(async () => {
        buttonWithText(container, labels.save).click();
      });
      expect(api.create).toHaveBeenCalledWith("workspace-1", starterContent);
    } finally {
      root.unmount();
    }
  });
});
