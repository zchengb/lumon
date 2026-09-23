import { Check, Clock3, GitBranch, LoaderCircle, Save } from "lucide-react";
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
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
}

const starterContent = [
  "---",
  'id = "my-flow"',
  'name = "My flow"',
  "enabled = true",
  'brief = "Describe the user request this flow handles."',
  "---",
  "",
  "# My flow",
  "",
  "## When to use",
  "",
  "Describe the request or business situation this flow handles.",
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
  "State what this flow does not cover and when another Agent or flow should be used.",
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
    <section className="panel settings-panel flow-schedule-panel">
      <div className="panel-heading">
        <div className="settings-title">
          <span className="settings-icon"><Clock3 size={18} /></span>
          <div><p className="eyebrow">{t("flows.eyebrow")}</p><h2>{t("flows.scheduleTitle")}</h2></div>
        </div>
        <div className="settings-heading-actions">
          <span className={enabled && selectedFlow.enabled ? "status-pill status-ready" : "status-pill status-neutral"}>
            {enabled && selectedFlow.enabled && <Check size={13} />}
            {enabled && selectedFlow.enabled ? t("flows.enabled") : t("flows.disabled")}
          </span>
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
      </div>
      <p className="settings-description">{t("flows.scheduleDescription")}</p>
      <div className="flow-schedule-fields">
        <label className="field-label" htmlFor="flow-schedule-expression">
          {t("flows.scheduleExpression")}
        </label>
        <input
          id="flow-schedule-expression"
          className="text-input mono"
          value={scheduleExpression}
          maxLength={128}
          placeholder="0 8 * * 1-5"
          onChange={(event) => {
            const nextExpression = event.target.value;
            setScheduleExpression(nextExpression);
            onDirtyChange(enabled !== savedEnabled || nextExpression !== savedExpression);
          }}
        />
        <p className="field-help">{t("flows.scheduleHelp")}</p>
        {!selectedFlow.enabled && <p className="field-help">{t("flows.scheduleFlowDisabled")}</p>}
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
    </section>
  );
}
