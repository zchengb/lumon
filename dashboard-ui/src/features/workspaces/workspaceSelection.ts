import type { WorkspaceListItem } from "../../shared/types";

export function resolveWorkspaceSelection(
  currentId: string | null,
  requestedId: string | null,
  workspaces: readonly WorkspaceListItem[],
): string | null {
  if (currentId && workspaces.some((workspace) => workspace.workspace_id === currentId)) {
    return currentId;
  }
  if (requestedId && workspaces.some((workspace) => workspace.workspace_id === requestedId)) {
    return requestedId;
  }
  return workspaces[0]?.workspace_id ?? null;
}
