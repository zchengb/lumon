import { describe, expect, it } from "vitest";
import { resolveWorkspaceSelection } from "./workspaceSelection";
import type { WorkspaceListItem } from "../../shared/types";

const workspaces: WorkspaceListItem[] = [
  { workspace_id: "first", name: "First", path: "/first", registered_at: "now", health: "ready", detail: "" },
  { workspace_id: "second", name: "Second", path: "/second", registered_at: "now", health: "ready", detail: "" },
];

describe("Workspace selection", () => {
  it("keeps the current Workspace when it is still registered", () => {
    expect(resolveWorkspaceSelection("second", "first", workspaces)).toBe("second");
  });

  it("uses the URL Workspace when the current selection is unavailable", () => {
    expect(resolveWorkspaceSelection("missing", "second", workspaces)).toBe("second");
  });

  it("falls back to the first Workspace or null", () => {
    expect(resolveWorkspaceSelection(null, null, workspaces)).toBe("first");
    expect(resolveWorkspaceSelection(null, null, [])).toBeNull();
  });
});
