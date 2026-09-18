import { Puzzle } from "lucide-react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { CapabilityDocument, CapabilitySummary } from "../../shared/types";
import {
  MarkdownDocumentsPage,
  type MarkdownDocumentApi,
  type MarkdownDocumentLabels,
} from "../shared/MarkdownDocumentsPage";

interface CapabilitiesPageProps {
  workspaceId: string;
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
}

const starterContent = [
  "---",
  'id = "my-capability"',
  'name = "My capability"',
  "enabled = true",
  'brief = "Describe what this capability helps the Agent do."',
  "---",
  "",
  "# My capability",
  "",
  "## Purpose",
  "",
  "Describe the Workspace knowledge, local tools, or operating guidance this capability provides.",
  "",
  "## When to use",
  "",
  "Describe the user request or situation where the Agent should consider this capability.",
  "",
  "## How to use",
  "",
  "1. List the evidence and Workspace paths to inspect.",
  "2. Describe the available commands or tools without embedding credentials.",
  "3. Explain how to validate the result.",
  "",
  "## Safety and limits",
  "",
  "Describe read-only defaults, confirmation requirements, sensitive data boundaries, and what this capability does not cover.",
  "",
].join("\n");

const capabilityApi: MarkdownDocumentApi<CapabilitySummary, CapabilityDocument> = {
  list: dashboardApi.listCapabilities,
  get: dashboardApi.getCapability,
  create: dashboardApi.createCapability,
  update: dashboardApi.updateCapability,
  delete: dashboardApi.deleteCapability,
};

export function CapabilitiesPage(props: CapabilitiesPageProps): React.JSX.Element {
  const { t } = useI18n();
  const labels: MarkdownDocumentLabels = {
    eyebrow: t("capabilities.eyebrow"),
    title: t("capabilities.title"),
    subtitle: t("capabilities.subtitle"),
    unsaved: t("capabilities.unsaved"),
    select: t("capabilities.select"),
    refresh: t("capabilities.refresh"),
    new: t("capabilities.new"),
    empty: t("capabilities.empty"),
    emptyHelp: t("capabilities.emptyHelp"),
    enabled: t("capabilities.enabled"),
    disabled: t("capabilities.disabled"),
    invalid: t("capabilities.invalid"),
    content: t("capabilities.content"),
    viewMode: t("capabilities.viewMode"),
    preview: t("capabilities.preview"),
    edit: t("capabilities.edit"),
    metadata: t("capabilities.metadata"),
    idHelp: t("capabilities.idHelp"),
    enable: t("capabilities.enable"),
    disable: t("capabilities.disable"),
    save: t("capabilities.save"),
    delete: t("capabilities.delete"),
    saved: t("capabilities.saved"),
    created: t("capabilities.created"),
    deleted: t("capabilities.deleted"),
    confirmDelete: t("capabilities.confirmDelete"),
    loadFailed: t("capabilities.loadFailed"),
    unsavedConfirm: t("app.unsavedViewConfirm"),
  };

  return (
    <MarkdownDocumentsPage
      {...props}
      icon={Puzzle}
      labels={labels}
      starterContent={starterContent}
      api={capabilityApi}
      getId={(document) => document.capability_id}
    />
  );
}
