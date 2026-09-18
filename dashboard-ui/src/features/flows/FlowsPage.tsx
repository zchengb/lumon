import { GitBranch } from "lucide-react";
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
    />
  );
}
