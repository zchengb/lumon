import { Clock3, GitBranch, LoaderCircle, Save } from "lucide-react";
import { useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { FlowDocument, FlowSummary } from "../../shared/types";
import {
  MarkdownDocumentsPage,
  type MarkdownDocumentApi,
  type MarkdownDocumentLabels,
} from "../shared/MarkdownDocumentsPage";

interface FlowsPageProps {
  workspaceId: string;
  initialDocumentId?: string;
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
}

const starterContent = [
  "---",
  'id = "my-flow"',
  'name = "My workflow"',
  "enabled = true",
  'brief = "Describe the user request this workflow handles."',
  "---",
  "",
  "# My workflow",
  "",
  "## When to use",
  "",
  "Describe the request or business situation this workflow handles.",
  "",
  "## Inputs and evidence",
  "",
  "List the files, links, user-provided context, and Workspace evidence to inspect.",
  "",
  "## Process",
  "",
  "1. Describe the first step and the decision it makes.",
  "2. Describe the next step, including tools or commands when needed.",
  "3. Describe validation, safety checks, and what to do when evidence is missing.",
  "",
  "## Output",
  "",
  "Describe the files, reply, or other result to produce and how to verify it.",
  "",
  "## Boundaries",
  "",
  "State what this workflow does not cover and when another Agent or workflow should be used.",
  "",
].join("\n");

const flowApi: MarkdownDocumentApi<FlowSummary, FlowDocument> = {
  list: dashboardApi.listFlows,
  get: dashboardApi.getFlow,
  create: dashboardApi.createFlow,
  update: dashboardApi.updateFlow,
  delete: dashboardApi.deleteFlow,
};

export function FlowsPage(props: FlowsPageProps): React.JSX.Element {
  const { t } = useI18n();
  const labels: MarkdownDocumentLabels = {
    eyebrow: t("flows.eyebrow"),
    title: t("flows.title"),
    subtitle: t("flows.subtitle"),
    unsaved: t("flows.unsaved"),
    select: t("flows.select"),
    refresh: t("flows.refresh"),
    new: t("flows.new"),
    empty: t("flows.empty"),
    emptyHelp: t("flows.emptyHelp"),
    enabled: t("flows.enabled"),
    disabled: t("flows.disabled"),
    invalid: t("flows.invalid"),
    content: t("flows.content"),
    viewMode: t("flows.viewMode"),
    preview: t("flows.preview"),
    edit: t("flows.edit"),
    metadata: t("flows.metadata"),
    idHelp: t("flows.idHelp"),
    enable: t("flows.enable"),
    disable: t("flows.disable"),
    save: t("flows.save"),
    delete: t("flows.delete"),
    saved: t("flows.saved"),
    created: t("flows.created"),
    deleted: t("flows.deleted"),
    confirmDelete: t("flows.confirmDelete"),
    loadFailed: t("flows.loadFailed"),
    unsavedConfirm: t("app.unsavedViewConfirm"),
  };

  return (
    <MarkdownDocumentsPage
      {...props}
      icon={GitBranch}
      labels={labels}
      starterContent={starterContent}
      api={flowApi}
      getId={(document) => document.flow_id}
      renderDetails={(document, markDirty) => (
        <FlowSchedulePanel
          key={document ? `${props.workspaceId}:${document.flow_id}:${document.enabled}:${document.schedule_enabled}:${document.schedule_expression}` : "none"}
          workspaceId={props.workspaceId}
          flow={document}
          onDirtyChange={markDirty}
          onNotice={props.onNotice}
          onError={props.onError}
        />
      )}
    />
  );
}

interface FlowSchedulePanelProps {
  workspaceId: string;
  flow: FlowDocument | null;
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
}

function FlowSchedulePanel({
  workspaceId,
  flow,
  onDirtyChange,
  onNotice,
  onError,
}: FlowSchedulePanelProps): React.JSX.Element | null {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(flow?.schedule_enabled ?? false);
  const [scheduleExpression, setScheduleExpression] = useState(
    flow?.schedule_expression ?? "0 8 * * *",
  );
  const [savedEnabled, setSavedEnabled] = useState(flow?.schedule_enabled ?? false);
  const [savedExpression, setSavedExpression] = useState(
    flow?.schedule_expression ?? "0 8 * * *",
  );
  const [saving, setSaving] = useState(false);

  if (!flow || !flow.valid) return null;
  const selectedFlow = flow;

  const changed = enabled !== savedEnabled || scheduleExpression !== savedExpression;

  async function saveSchedule(): Promise<void> {
    setSaving(true);
    try {
      const saved = await dashboardApi.updateFlowSchedule(
        workspaceId,
        selectedFlow.flow_id,
        enabled,
        scheduleExpression.trim(),
      );
      setEnabled(saved.schedule_enabled);
      setSavedEnabled(saved.schedule_enabled);
      setScheduleExpression(saved.schedule_expression);
      setSavedExpression(saved.schedule_expression);
      onDirtyChange(false);
      onNotice(t("flows.scheduleSaved"));
    } catch (reason) {
      onError(reason instanceof Error ? reason.message : t("flows.loadFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="flow-schedule-panel" aria-label={t("flows.scheduleTitle")}>
      <div className="flow-schedule-heading">
        <h3><Clock3 size={16} />{t("flows.scheduleTitle")}</h3>
        <label className={`settings-toggle ${enabled ? "is-enabled" : ""}`}>
          <span>{t("flows.scheduleToggle")}</span>
          <input
            type="checkbox"
            role="switch"
            checked={enabled}
            disabled={!selectedFlow.enabled}
            aria-label={t("flows.scheduleToggle")}
            onChange={(event) => {
              const nextEnabled = event.target.checked;
              setEnabled(nextEnabled);
              onDirtyChange(
                nextEnabled !== savedEnabled || scheduleExpression !== savedExpression,
              );
            }}
          />
          <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
        </label>
      </div>
      <div className="flow-schedule-form">
        <div className="flow-schedule-fields">
          <label className="field-label" htmlFor="flow-schedule-expression">
            {t("flows.scheduleExpression")}
          </label>
          <input
            id="flow-schedule-expression"
            className="text-input mono"
            value={scheduleExpression}
            maxLength={128}
            aria-describedby="flow-schedule-help"
            placeholder="0 8 * * 1-5"
            onChange={(event) => {
              const nextExpression = event.target.value;
              setScheduleExpression(nextExpression);
              onDirtyChange(enabled !== savedEnabled || nextExpression !== savedExpression);
            }}
          />
        </div>
        <div className="settings-actions">
          <button
            className="button button-primary"
            type="button"
            onClick={() => void saveSchedule()}
            disabled={saving || !changed || (enabled && !selectedFlow.enabled)}
          >
            {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
            {t("flows.scheduleSave")}
          </button>
        </div>
      </div>
      <p className="field-help">{t("flows.scheduleDescription")}</p>
      <p id="flow-schedule-help" className="field-help">{t("flows.scheduleHelp")}</p>
      {!selectedFlow.enabled && <p className="field-help">{t("flows.scheduleFlowDisabled")}</p>}
    </section>
  );
}
