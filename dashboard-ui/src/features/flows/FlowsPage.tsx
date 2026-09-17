import {
  AlertTriangle,
  Check,
  FilePlus2,
  GitBranch,
  LoaderCircle,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { FlowDocument, FlowSummary } from "../../shared/types";

interface FlowsPageProps {
  workspaceId: string;
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
}

const starterContent = `---
id = "my-flow"
name = "My flow"
enabled = true
brief = "Describe when this flow should be used."
match = ["example request"]
---

# My flow

## When to use

Describe the user request this flow handles.

## Process

1. Describe the first step.
2. Describe the next step and the tools or commands to use.

## Output

Describe the files, reply, or other result to produce.
`;

export function FlowsPage({
  workspaceId,
  onDirtyChange,
  onNotice,
  onError,
}: FlowsPageProps): React.JSX.Element {
  const { t } = useI18n();
  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [document, setDocument] = useState<FlowDocument | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setDocument(null);
    setContent("");
    setSelectedId(null);
    onDirtyChange(false);
    void dashboardApi
      .listFlows(workspaceId)
      .then((nextFlows) => {
        if (cancelled) return;
        setFlows(nextFlows);
      })
      .catch((reason: unknown) => {
        if (!cancelled) onError(messageFor(reason, t("flows.loadFailed")));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [onDirtyChange, onError, t, workspaceId]);

  async function selectFlow(flow: FlowSummary): Promise<void> {
    if (flow.flow_id === selectedId) return;
    if (!confirmDiscard()) return;
    setSelectedId(flow.flow_id);
    setDocument(null);
    setContent("");
    onDirtyChange(false);
    setLoadingDocument(true);
    try {
      const nextDocument = await dashboardApi.getFlow(workspaceId, flow.flow_id);
      setDocument(nextDocument);
      setContent(nextDocument.content);
    } catch (reason) {
      onError(messageFor(reason, t("flows.loadFailed")));
    } finally {
      setLoadingDocument(false);
    }
  }

  async function createFlow(): Promise<void> {
    if (!confirmDiscard()) return;
    setSaving(true);
    try {
      const nextDocument = await dashboardApi.createFlow(workspaceId, starterContent);
      setDocument(nextDocument);
      setContent(nextDocument.content);
      setSelectedId(nextDocument.flow_id);
      onDirtyChange(false);
      await reloadFlows(nextDocument.flow_id);
      onNotice(t("flows.created"));
    } catch (reason) {
      onError(messageFor(reason, t("flows.loadFailed")));
    } finally {
      setSaving(false);
    }
  }

  async function saveFlow(): Promise<void> {
    if (!document || !selectedId) return;
    setSaving(true);
    try {
      const saved = await dashboardApi.updateFlow(workspaceId, selectedId, content);
      setDocument(saved);
      setContent(saved.content);
      onDirtyChange(false);
      await reloadFlows(saved.flow_id);
      onNotice(t("flows.saved"));
    } catch (reason) {
      onError(messageFor(reason, t("flows.loadFailed")));
    } finally {
      setSaving(false);
    }
  }

  async function deleteFlow(): Promise<void> {
    if (!selectedId || !document || !window.confirm(t("flows.confirmDelete"))) return;
    setDeleting(true);
    try {
      await dashboardApi.deleteFlow(workspaceId, selectedId);
      const deletedId = selectedId;
      setSelectedId(null);
      setDocument(null);
      setContent("");
      onDirtyChange(false);
      await reloadFlows(null, deletedId);
      onNotice(t("flows.deleted"));
    } catch (reason) {
      onError(messageFor(reason, t("flows.loadFailed")));
    } finally {
      setDeleting(false);
    }
  }

  async function reloadFlows(preferredId: string | null, removedId?: string): Promise<void> {
    const nextFlows = await dashboardApi.listFlows(workspaceId);
    setFlows(nextFlows);
    if (removedId && selectedId === removedId) setSelectedId(null);
    if (preferredId && !nextFlows.some((flow) => flow.flow_id === preferredId)) {
      setSelectedId(null);
    }
  }

  function confirmDiscard(): boolean {
    if (document && content !== document.content) {
      return window.confirm(t("app.unsavedViewConfirm"));
    }
    return true;
  }

  const dirty = document !== null && content !== document.content;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("flows.eyebrow")}</p>
          <h1>{t("flows.title")}</h1>
          <p className="muted">{t("flows.subtitle")}</p>
        </div>
        {dirty && <span className="unsaved-label">{t("flows.unsaved")}</span>}
      </div>

      <div className="flows-layout">
        <section className="panel flows-list-panel">
          <div className="panel-heading flows-panel-heading">
            <div className="settings-title">
              <span className="settings-icon"><GitBranch size={18} /></span>
              <div><p className="eyebrow">{t("flows.eyebrow")}</p><h2>{t("flows.select")}</h2></div>
            </div>
            <button className="icon-button" type="button" onClick={() => void refresh()} disabled={loading} aria-label={t("flows.refresh")}>
              <RefreshCw size={15} className={loading ? "spin" : ""} />
            </button>
          </div>
          <div className="flows-list-actions">
            <button className="button button-primary" type="button" onClick={() => void createFlow()} disabled={saving}>
              {saving ? <LoaderCircle size={15} className="spin" /> : <FilePlus2 size={15} />}
              {t("flows.new")}
            </button>
          </div>
          {loading ? (
            <div className="loading-inline flows-loading"><LoaderCircle size={20} className="spin" />{t("app.loading")}</div>
          ) : flows.length === 0 ? (
            <div className="empty-inline"><GitBranch size={22} /><div><strong>{t("flows.empty")}</strong><p>{t("flows.emptyHelp")}</p></div></div>
          ) : (
            <div className="flows-list">
              {flows.map((flow) => (
                <button
                  className={`flow-row ${flow.flow_id === selectedId ? "active" : ""}`}
                  type="button"
                  key={`${flow.path}:${flow.flow_id}`}
                  onClick={() => void selectFlow(flow)}
                >
                  <span className="flow-row-icon">{flow.valid ? <GitBranch size={15} /> : <AlertTriangle size={15} />}</span>
                  <span className="flow-row-copy"><strong>{flow.name || flow.flow_id}</strong><small>{flow.path}</small>{!flow.valid && <em>{flow.error ?? t("flows.invalid")}</em>}</span>
                  <span className={flow.valid && flow.enabled ? "status-pill status-ready" : "status-pill status-neutral"}>{flow.valid && flow.enabled ? <><Check size={12} />{t("flows.valid")}</> : t("flows.invalid")}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="panel flow-editor-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">{t("flows.content")}</p><h2>{document?.name ?? t("flows.select")}</h2></div>
            {document && <span className="mono flow-editor-path">{document.path}</span>}
          </div>
          {loadingDocument ? (
            <div className="loading-inline"><LoaderCircle size={20} className="spin" />{t("app.loading")}</div>
          ) : document ? (
            <>
              <textarea
                className="flow-editor"
                value={content}
                aria-label={t("flows.content")}
                onChange={(event) => { setContent(event.target.value); onDirtyChange(event.target.value !== document.content); }}
                spellCheck={false}
              />
              {document.error && <p className="flow-editor-error"><AlertTriangle size={14} />{document.error}</p>}
              <div className="flow-editor-actions">
                <button className="button button-secondary" type="button" onClick={() => void deleteFlow()} disabled={deleting || saving}>
                  {deleting ? <LoaderCircle size={15} className="spin" /> : <Trash2 size={15} />}{t("flows.delete")}
                </button>
                <button className="button button-primary" type="button" onClick={() => void saveFlow()} disabled={saving || deleting || !dirty}>
                  {saving ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}{t("flows.save")}
                </button>
              </div>
            </>
          ) : (
            <div className="empty-inline flow-editor-empty"><GitBranch size={24} /><div><strong>{t("flows.select")}</strong><p>{t("flows.idHelp")}</p></div></div>
          )}
        </section>
      </div>
    </div>
  );

  async function refresh(): Promise<void> {
    setLoading(true);
    try {
      const nextFlows = await dashboardApi.listFlows(workspaceId);
      setFlows(nextFlows);
    } catch (reason) {
      onError(messageFor(reason, t("flows.loadFailed")));
    } finally {
      setLoading(false);
    }
  }
}

function messageFor(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
