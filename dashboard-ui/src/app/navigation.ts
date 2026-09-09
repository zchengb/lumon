import type { View } from "../shared/types";

const views: View[] = ["overview", "settings"];

export interface NavigationState {
  workspaceId: string | null;
  view: View;
}

export function readNavigation(search: string): NavigationState {
  const params = new URLSearchParams(search);
  const requestedView = params.get("view");
  return {
    workspaceId: params.get("workspace"),
    view: views.includes(requestedView as View) ? (requestedView as View) : "overview",
  };
}

export function writeNavigation(state: NavigationState): string {
  const params = new URLSearchParams();
  if (state.workspaceId) params.set("workspace", state.workspaceId);
  params.set("view", state.view);
  return `?${params.toString()}`;
}
