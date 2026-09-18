import {
  AlertTriangle,
  Check,
  Eye,
  FilePlus2,
  LoaderCircle,
  PencilLine,
  Power,
  RefreshCw,
  Save,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { MarkdownPreview } from "../flows/MarkdownPreview";

export interface MarkdownDocumentSummary {
  name: string;
  enabled: boolean;
  brief: string;
  path: string;
  valid: boolean;
  error: string | null;
}

export interface MarkdownDocumentContent {
  content: string;
}

export interface MarkdownDocumentApi<
  TSummary extends MarkdownDocumentSummary,
  TDocument extends TSummary & MarkdownDocumentContent,
> {
  list: (workspaceId: string) => Promise<TSummary[]>;
  get: (workspaceId: string, id: string) => Promise<TDocument>;
  create: (workspaceId: string, content: string) => Promise<TDocument>;
  update: (workspaceId: string, id: string, content: string) => Promise<TDocument>;
  delete: (workspaceId: string, id: string) => Promise<void>;
}

export interface MarkdownDocumentLabels {
  eyebrow: string;
  title: string;
  subtitle: string;
  unsaved: string;
  select: string;
  refresh: string;
  new: string;
  empty: string;
  emptyHelp: string;
  enabled: string;
  disabled: string;
  invalid: string;
  content: string;
  viewMode: string;
  preview: string;
  edit: string;
  metadata: string;
  idHelp: string;
  enable: string;
  disable: string;
  save: string;
  delete: string;
  saved: string;
  created: string;
  deleted: string;
  confirmDelete: string;
  loadFailed: string;
  unsavedConfirm: string;
}

interface MarkdownDocumentsPageProps<
  TSummary extends MarkdownDocumentSummary,
  TDocument extends TSummary & MarkdownDocumentContent,
> {
  workspaceId: string;
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
  icon: LucideIcon;
  labels: MarkdownDocumentLabels;
  starterContent: string;
  api: MarkdownDocumentApi<TSummary, TDocument>;
  getId: (document: TSummary) => string;
}

type DocumentViewMode = "preview" | "edit";

export function MarkdownDocumentsPage<
  TSummary extends MarkdownDocumentSummary,
  TDocument extends TSummary & MarkdownDocumentContent,
>({
  workspaceId,
  onDirtyChange,
  onNotice,
  onError,
  icon: DocumentIcon,
  labels,
  starterContent,
  api,
  getId,
}: MarkdownDocumentsPageProps<TSummary, TDocument>): React.JSX.Element {
  const [documents, setDocuments] = useState<TSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [document, setDocument] = useState<TDocument | null>(null);
  const [draft, setDraft] = useState(false);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [viewMode, setViewMode] = useState<DocumentViewMode>("preview");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setDocument(null);
    setDraft(false);
    setContent("");
    setSelectedId(null);
    setViewMode("preview");
    onDirtyChange(false);
    void api.list(workspaceId)
      .then((nextDocuments) => {
        if (!cancelled) setDocuments(nextDocuments);
      })
      .catch((reason: unknown) => {
        if (!cancelled) onError(messageFor(reason, labels.loadFailed));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [api, labels.loadFailed, onDirtyChange, onError, workspaceId]);

  async function selectDocument(summary: TSummary): Promise<void> {
    const nextId = getId(summary);
    if (nextId === selectedId) return;
    if (!confirmDiscard()) return;
    setSelectedId(nextId);
    setDocument(null);
    setDraft(false);
    setContent("");
    setViewMode("preview");
    onDirtyChange(false);
    setLoadingDocument(true);
    try {
      const nextDocument = await api.get(workspaceId, nextId);
      setDocument(nextDocument);
      setContent(nextDocument.content);
    } catch (reason) {
      onError(messageFor(reason, labels.loadFailed));
    } finally {
      setLoadingDocument(false);
    }
  }

  async function createDocument(): Promise<void> {
    if (!confirmDiscard()) return;
    setSelectedId(null);
    setDocument(null);
    setDraft(true);
    setContent(starterContent);
    setViewMode("edit");
    onDirtyChange(true);
  }

  async function saveDocument(): Promise<void> {
    if (!draft && (!document || !selectedId)) return;
    setSaving(true);
    try {
      let saved: TDocument;
      if (draft) {
        saved = await api.create(workspaceId, content);
      } else {
        if (!document || !selectedId) return;
        saved = await api.update(workspaceId, selectedId, content);
      }
      setDocument(saved);
      setDraft(false);
      setContent(saved.content);
      setSelectedId(getId(saved));
      onDirtyChange(false);
      await reloadDocuments(getId(saved));
      onNotice(draft ? labels.created : labels.saved);
    } catch (reason) {
      onError(messageFor(reason, labels.loadFailed));
    } finally {
      setSaving(false);
    }
  }

  async function toggleDocument(): Promise<void> {
    if (!document || !selectedId || !document.valid) return;
    if (!confirmDiscard()) return;
    const nextContent = replaceEnabledFlag(content, !document.enabled);
    if (!nextContent) {
      onError(labels.loadFailed);
      return;
    }
    setSaving(true);
    try {
      const saved = await api.update(workspaceId, selectedId, nextContent);
      setDocument(saved);
      setContent(saved.content);
      onDirtyChange(false);
      await reloadDocuments(getId(saved));
      onNotice(labels.saved);
    } catch (reason) {
      onError(messageFor(reason, labels.loadFailed));
    } finally {
      setSaving(false);
    }
  }

  async function deleteDocument(): Promise<void> {
    if (!selectedId || !document || !window.confirm(labels.confirmDelete)) return;
    setDeleting(true);
    try {
      await api.delete(workspaceId, selectedId);
      const deletedId = selectedId;
      setSelectedId(null);
      setDocument(null);
      setDraft(false);
      setContent("");
      setViewMode("preview");
      onDirtyChange(false);
      await reloadDocuments(null, deletedId);
      onNotice(labels.deleted);
    } catch (reason) {
      onError(messageFor(reason, labels.loadFailed));
    } finally {
      setDeleting(false);
    }
  }

  async function reloadDocuments(preferredId: string | null, removedId?: string): Promise<void> {
    const nextDocuments = await api.list(workspaceId);
    setDocuments(nextDocuments);
    if (removedId && selectedId === removedId) setSelectedId(null);
    if (preferredId && !nextDocuments.some((item) => getId(item) === preferredId)) {
      setSelectedId(null);
    }
  }

  async function refresh(): Promise<void> {
    setLoading(true);
    try {
      setDocuments(await api.list(workspaceId));
    } catch (reason) {
      onError(messageFor(reason, labels.loadFailed));
    } finally {
      setLoading(false);
    }
  }

  function confirmDiscard(): boolean {
    if (draft || (document && content !== document.content)) {
      return window.confirm(labels.unsavedConfirm);
    }
    return true;
  }

  const dirty = draft || (document !== null && content !== document.content);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{labels.eyebrow}</p>
          <h1>{labels.title}</h1>
          <p className="muted">{labels.subtitle}</p>
        </div>
        {dirty && <span className="unsaved-label">{labels.unsaved}</span>}
      </div>

      <div className="flows-layout">
        <section className="panel flows-list-panel">
          <div className="panel-heading flows-panel-heading">
            <div className="settings-title">
              <span className="settings-icon"><DocumentIcon size={18} /></span>
              <div><p className="eyebrow">{labels.eyebrow}</p><h2>{labels.select}</h2></div>
            </div>
            <button className="icon-button" type="button" onClick={() => void refresh()} disabled={loading} aria-label={labels.refresh}>
              <RefreshCw size={15} className={loading ? "spin" : ""} />
            </button>
          </div>
          <div className="flows-list-actions">
            <button className="button button-primary" type="button" onClick={() => void createDocument()} disabled={saving}>
              {saving ? <LoaderCircle size={15} className="spin" /> : <FilePlus2 size={15} />}
              {labels.new}
            </button>
          </div>
          {loading ? (
            <div className="loading-inline flows-loading"><LoaderCircle size={20} className="spin" />Loading…</div>
          ) : documents.length === 0 ? (
            <div className="empty-inline"><DocumentIcon size={22} /><div><strong>{labels.empty}</strong><p>{labels.emptyHelp}</p></div></div>
          ) : (
            <div className="flows-list">
              {documents.map((summary) => {
                const id = getId(summary);
                const statusLabel = !summary.valid
                  ? labels.invalid
                  : summary.enabled
                    ? labels.enabled
                    : labels.disabled;
                return (
                  <button
                    className={"flow-row" + (id === selectedId ? " active" : "")}
                    type="button"
                    key={summary.path + ":" + id}
                    onClick={() => void selectDocument(summary)}
                  >
                    <span className="flow-row-icon">{summary.valid ? <DocumentIcon size={15} /> : <AlertTriangle size={15} />}</span>
                    <span className="flow-row-copy"><strong>{summary.name || id}</strong><small>{summary.path}</small>{!summary.valid && <em>{summary.error ?? labels.invalid}</em>}</span>
                    <span className={summary.valid && summary.enabled ? "status-pill status-ready" : "status-pill status-neutral"}>{summary.valid && summary.enabled ? <><Check size={12} />{statusLabel}</> : statusLabel}</span>
                  </button>
                );
              })}
            </div>
          )}
        </section>

        <section className="panel flow-editor-panel">
          <div className="panel-heading flow-editor-heading">
            <div><p className="eyebrow">{labels.content}</p><h2>{document?.name ?? (draft ? labels.new : labels.select)}</h2></div>
            {document && (
              <div className="flow-editor-heading-actions">
                <span className="mono flow-editor-path">{document.path}</span>
                <div className="segmented-control flow-view-toggle" role="group" aria-label={labels.viewMode}>
                  <button className={viewMode === "preview" ? "active" : ""} type="button" aria-pressed={viewMode === "preview"} onClick={() => setViewMode("preview")}>
                    <Eye size={14} />{labels.preview}
                  </button>
                  <button className={viewMode === "edit" ? "active" : ""} type="button" aria-pressed={viewMode === "edit"} onClick={() => setViewMode("edit")}>
                    <PencilLine size={14} />{labels.edit}
                  </button>
                </div>
              </div>
            )}
          </div>
          {loadingDocument ? (
            <div className="loading-inline"><LoaderCircle size={20} className="spin" />Loading…</div>
          ) : document || draft ? (
            <>
              {viewMode === "preview" ? (
                <MarkdownPreview content={content} metadataLabel={labels.metadata} />
              ) : (
                <textarea
                  className="flow-editor"
                  value={content}
                  aria-label={labels.content}
                  onChange={(event) => {
                    setContent(event.target.value);
                    onDirtyChange(draft || (document !== null && event.target.value !== document.content));
                  }}
                  spellCheck={false}
                />
              )}
              {document?.error && <p className="flow-editor-error"><AlertTriangle size={14} />{document.error}</p>}
              <div className="flow-editor-actions">
                {document?.valid && (
                  <button className="button button-secondary" type="button" onClick={() => void toggleDocument()} disabled={deleting || saving}>
                    {saving ? <LoaderCircle size={15} className="spin" /> : <Power size={15} />}
                    {document.enabled ? labels.disable : labels.enable}
                  </button>
                )}
                {document && (
                  <button className="button button-secondary" type="button" onClick={() => void deleteDocument()} disabled={deleting || saving}>
                    {deleting ? <LoaderCircle size={15} className="spin" /> : <Trash2 size={15} />}{labels.delete}
                  </button>
                )}
                <button className="button button-primary" type="button" onClick={() => void saveDocument()} disabled={saving || deleting || !dirty}>
                  {saving ? <LoaderCircle size={15} className="spin" /> : <Save size={15} />}{labels.save}
                </button>
              </div>
            </>
          ) : (
            <div className="empty-inline flow-editor-empty"><DocumentIcon size={24} /><div><strong>{labels.select}</strong><p>{labels.idHelp}</p></div></div>
          )}
        </section>
      </div>
    </div>
  );
}

function replaceEnabledFlag(content: string, enabled: boolean): string | null {
  const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(content);
  if (!frontmatter) return null;
  const enabledLine = /^(\s*enabled\s*=\s*)(true|false)(\s*)$/m;
  if (!enabledLine.test(frontmatter[1])) return null;
  const nextFrontmatter = frontmatter[1].replace(
    enabledLine,
    (_match, prefix: string, _current: string, suffix: string) =>
      prefix + String(enabled) + suffix,
  );
  return content.replace(frontmatter[1], nextFrontmatter);
}

function messageFor(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
