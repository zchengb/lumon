import { ChevronDown, CircleAlert } from "lucide-react";
import { useI18n } from "../../shared/i18n";
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
  const { t } = useI18n();

  return (
    <label className="workspace-picker">
      <span className="sr-only">{t("picker.currentWorkspace")}</span>
      <select
        aria-label={t("picker.currentWorkspace")}
        value={selectedId ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        {workspaces.map((workspace) => (
          <option key={workspace.workspace_id} value={workspace.workspace_id}>
            {workspace.name}
            {workspace.health === "ready" ? "" : ` · ${t("picker.needsCheck")}`}
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
  const { t } = useI18n();

  if (health === "ready") {
    return <span className="status-pill status-ready">{t("health.available")}</span>;
  }
  return (
    <span className="status-pill status-warning">
      <CircleAlert size={13} aria-hidden="true" />
      {health === "missing" ? t("health.pathMissing") : t("health.invalidConfig")}
    </span>
  );
}
