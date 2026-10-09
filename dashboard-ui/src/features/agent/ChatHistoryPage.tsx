import { ChevronDown, ChevronUp, ExternalLink, LoaderCircle, MessageSquare, RefreshCw, Search, UserRound, UsersRound } from "lucide-react";
import { useEffect, useId, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ApiError, dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { ChatInteraction, ChatInteractionDetail, ChatInteractionPage, ChatKind } from "../../shared/types";

export function ChatHistoryPage({ workspaceId }: { workspaceId: string }): React.JSX.Element {
  const { locale, t } = useI18n();
  const [kind, setKind] = useState<ChatKind>("all");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<ChatInteractionPage>({ items: [], total: 0 });
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPage({ items: [], total: 0 });
    dashboardApi.listConversations(workspaceId, kind, search, offset)
      .then((next) => { if (!cancelled) setPage(next); })
      .catch((reason: unknown) => { if (!cancelled) setError(reason instanceof ApiError ? reason : new Error()); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [workspaceId, kind, search, offset, refresh]);

  function timeLabel(timestamp: string): string {
    const date = new Date(timestamp);
    return Number.isNaN(date.valueOf()) ? "—" : date.toLocaleString(locale, {
      month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  }

  return <div className="page-stack">
    <div className="page-heading">
      <div><h1>{t("app.agentSettings")}</h1><p className="muted">{t("chat.subtitle")}</p></div>
      <button className="button button-secondary" type="button" onClick={() => setRefresh((value) => value + 1)} disabled={loading}>
        <RefreshCw size={15} />{t("overview.refresh")}
      </button>
    </div>
    <section className="panel chat-activity" aria-label={t("chat.title")}>
      <div className="panel-heading"><h2>{t("chat.title")}</h2><span className="muted">{page.total}</span></div>
      <form className="chat-filters" onSubmit={(event) => { event.preventDefault(); setOffset(0); setSearch(searchInput.trim()); setRefresh((value) => value + 1); }}>
        <label className="sr-only" htmlFor="chat-kind">{t("chat.type")}</label>
        <select id="chat-kind" className="text-input" value={kind} onChange={(event) => { setOffset(0); setKind(event.target.value as ChatKind); }}>
          <option value="all">{t("chat.all")}</option><option value="group">{t("chat.group")}</option><option value="direct">{t("chat.direct")}</option>
        </select>
        <div className="chat-search">
          <label className="sr-only" htmlFor="chat-search">{t("chat.search")}</label>
          <input id="chat-search" className="text-input" value={searchInput} maxLength={200} placeholder={t("chat.search")} onChange={(event) => setSearchInput(event.target.value)} />
          <button className="icon-button" type="submit" aria-label={t("chat.search")}><Search size={16} /></button>
        </div>
      </form>
      {error ? <p className="chat-empty" role="alert">{error instanceof ApiError ? error.message : t("app.dashboardRequestFailed")}</p>
        : loading ? <div className="loading-inline" role="status"><LoaderCircle size={18} className="spin" />{t("chat.loading")}</div>
          : page.items.length ? <div className="table-scroll chat-table-scroll" tabIndex={0} role="region" aria-label={t("chat.title")}>
            <table className="scan-history-table chat-activity-table">
              <colgroup><col className="chat-time-column" /><col className="chat-source-column" /><col className="chat-user-column" /><col className="chat-text-column" /><col className="chat-text-column" /><col className="chat-status-column" /><col className="chat-duration-column" /><col className="chat-trace-column" /></colgroup>
              <thead><tr><th scope="col">{t("autoScan.started")}</th><th scope="col">{t("chat.source")}</th><th scope="col">{t("chat.user")}</th><th scope="col">{t("chat.input")}</th><th scope="col">{t("chat.output")}</th><th scope="col">{t("autoScan.status")}</th><th scope="col">{t("autoScan.duration")}</th><th scope="col">Langfuse</th></tr></thead>
              <tbody>{page.items.map((interaction) => <InteractionRow key={`${workspaceId}:${interaction.run_id}`} workspaceId={workspaceId} interaction={interaction} timeLabel={timeLabel(interaction.started_at)} />)}</tbody>
            </table>
          </div> : <div className="chat-empty"><MessageSquare size={22} /><p>{t("chat.empty")}</p></div>}
      {page.total > 20 && <div className="chat-pagination">
        <button className="button button-secondary" type="button" disabled={loading || offset === 0} onClick={() => setOffset((value) => value - 20)}>{t("autoScan.previous")}</button>
        <span className="muted">{Math.floor(offset / 20) + 1} / {Math.ceil(page.total / 20)}</span>
        <button className="button button-secondary" type="button" disabled={loading || offset + 20 >= page.total} onClick={() => setOffset((value) => value + 20)}>{t("autoScan.next")}</button>
      </div>}
    </section>
  </div>;
}

type MessageColumn = "input" | "output";

function InteractionRow({ workspaceId, interaction, timeLabel }: {
  workspaceId: string; interaction: ChatInteraction; timeLabel: string;
}): React.JSX.Element {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState({ input: false, output: false });
  const [detail, setDetail] = useState<ChatInteractionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const needsDetail = (expanded.input || expanded.output) && !detail;

  useEffect(() => {
    if (!needsDetail) return;
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    dashboardApi.getConversation(workspaceId, interaction.run_id)
      .then((next) => { if (!cancelled) setDetail(next); })
      .catch(() => { if (!cancelled) setFailed(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [needsDetail, workspaceId, interaction.run_id, retry]);

  const direct = ["p2p", "private", "dm"].includes(interaction.chat_type.toLowerCase());
  const sourceName = direct ? null : interaction.chat_name;
  const traceUrl = interaction.trace_url ? safeLink(interaction.trace_url) : "";
  return <tr>
    <td><time dateTime={interaction.started_at}>{timeLabel}</time></td>
    <td><span className={`chat-source-tag ${direct ? "chat-source-direct" : "chat-source-group"}`}>{direct ? <UserRound size={12} aria-hidden="true" /> : <UsersRound size={12} aria-hidden="true" />}{direct ? t("chat.direct") : t("chat.group")}</span>{sourceName && <span className="chat-display-name" title={sourceName}>{sourceName}</span>}</td>
    <td>{interaction.sender_name && <span className="chat-display-name" title={interaction.sender_name}>{interaction.sender_name}</span>}<span className="chat-id mono" title={interaction.sender_id}>{identifierLabel(interaction.sender_id)}</span></td>
    {(["input", "output"] as const).map((column) => <MessageCell key={column} column={column} preview={column === "input" ? interaction.input_preview : interaction.output_preview} text={detail ? (column === "input" ? detail.input_text : detail.output_text) : null} expanded={expanded[column]} loading={loading} failed={failed} onToggle={() => {
      if (!expanded[column] && failed) setRetry((count) => count + 1);
      setExpanded((current) => ({ ...current, [column]: !current[column] }));
    }} />)}
    <td><RunStatus status={interaction.status} /></td>
    <td className="chat-duration">{interaction.duration_seconds === null ? "—" : `${Math.floor(interaction.duration_seconds / 60)}m${interaction.duration_seconds % 60}s`}</td>
    <td className="chat-trace">{traceUrl ? <a className="chat-trace-link" href={traceUrl} target="_blank" rel="noopener noreferrer" aria-label={`${t("chat.viewTrace")} · ${timeLabel}`}>{t("chat.viewTrace")}<ExternalLink size={12} aria-hidden="true" /></a> : "—"}</td>
  </tr>;
}

function MessageCell({ column, preview, text, expanded, loading, failed, onToggle }: {
  column: MessageColumn; preview: string; text: string | null; expanded: boolean;
  loading: boolean; failed: boolean; onToggle: () => void;
}): React.JSX.Element {
  const { t } = useI18n();
  const id = useId();
  const content = expanded && text !== null ? text : preview;
  const action = expanded ? t("chat.collapse") : t("chat.expand");
  return <td>
    <div id={id} className={`chat-summary chat-${column}${expanded ? " chat-message-expanded" : ""}`}>
      {column === "output" ? <MessageMarkdown text={content || "—"} /> : content || "—"}
    </div>
    {expanded && loading && <span className="chat-message-note" role="status">{t("chat.messageLoading")}</span>}
    {expanded && failed && <span className="chat-message-note" role="alert">{t("chat.messageFailed")}</span>}
    {preview && <button className="chat-message-toggle" type="button" aria-expanded={expanded} aria-controls={id} aria-label={`${action} ${t(`chat.${column}`)}`} onClick={onToggle}>{action}{expanded ? <ChevronUp size={12} aria-hidden="true" /> : <ChevronDown size={12} aria-hidden="true" />}</button>}
  </td>;
}

function MessageMarkdown({ text }: { text: string }): React.JSX.Element {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml disallowedElements={["img"]} urlTransform={safeLink} components={{ a: ({ children, href }) => href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span> }}>{text}</ReactMarkdown>;
}

function identifierLabel(identifier: string): string {
  return identifier.length > 20 ? `${identifier.slice(0, 6)}…${identifier.slice(-4)}` : identifier;
}

function safeLink(url: string): string {
  try {
    const parsed = new URL(url);
    return ["https:", "http:"].includes(parsed.protocol) && !parsed.username && !parsed.password ? url : "";
  } catch {
    return "";
  }
}

function RunStatus({ status }: { status: string }): React.JSX.Element {
  const { t } = useI18n();
  const labels: Record<string, string> = {
    running: t("chat.running"), succeeded: t("chat.succeeded"), failed: t("chat.failed"),
    timed_out: t("chat.timedOut"), interrupted: t("chat.interrupted"), cancelled: t("chat.cancelled"),
  };
  const tone = status === "succeeded" ? "status-ready" : status === "running" ? "status-warning" : "status-danger";
  return <span className={`status-pill ${tone}`}>{labels[status] ?? status}</span>;
}
