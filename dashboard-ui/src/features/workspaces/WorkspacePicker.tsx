import { ChevronDown, CircleAlert } from "lucide-react";
import type { WorkspaceListItem } from "../../shared/types";

interface WorkspacePickerProps {
  workspaces: WorkspaceListItem[];
  selectedId: string | null;
  onChange: (workspaceId: string) => void;
}

export function WorkspacePicker({
  workspaces,
  selectedId,
  onChange,
}: WorkspacePickerProps): React.JSX.Element {
  return (
    <label className="workspace-picker">
      <span className="sr-only">当前 Workspace</span>
      <select
        aria-label="当前 Workspace"
        value={selectedId ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        {workspaces.map((workspace) => (
          <option key={workspace.workspace_id} value={workspace.workspace_id}>
            {workspace.name}
            {workspace.health === "ready" ? "" : " · 需要检查"}
          </option>
        ))}
      </select>
      <ChevronDown size={16} aria-hidden="true" />
    </label>
  );
}

export function WorkspaceHealthLabel({
  health,
}: Pick<WorkspaceListItem, "health">): React.JSX.Element {
  if (health === "ready") {
    return <span className="status-pill status-ready">可用</span>;
  }
  return (
    <span className="status-pill status-warning">
      <CircleAlert size={13} aria-hidden="true" />
      {health === "missing" ? "路径不存在" : "配置异常"}
    </span>
  );
}
