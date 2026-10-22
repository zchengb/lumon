import { Check, Clock3, ExternalLink, LoaderCircle, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, dashboardApi } from "../../app/api";
import { useI18n, type Translator } from "../../shared/i18n";
import type { DeliveryActivity, DeliveryHistory, DeliveryPoll, DeliveryRun } from "../../shared/types";

const stages = ["discover", "claim", "implementation", "verification", "handoff"] as const;

export function DeliveryHistoryPanel({ workspaceId, onError }: {
  workspaceId: string; onError: (message: string | null) => void;
}): React.JSX.Element {
  const { locale, t } = useI18n();
  const [history, setHistory] = useState<DeliveryHistory>({ runs: [], polls: [] });
  const [activity, setActivity] = useState<DeliveryActivity[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(Date.now());
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    if (deleting !== null) return;
    let cancelled = false;
    let timer: number | undefined;
    async function load(): Promise<void> {
      try {
        const next = await dashboardApi.getDeliveryHistory(workspaceId);
        if (cancelled) return;
        setHistory(next);
        setNow(Date.now());
        const poll = next.polls.find((item) => item.run_id === selectedId) ?? (selectedId ? undefined : next.polls[0]);
        const run = next.runs.find((item) => item.run_id === selectedId)
          ?? (!selectedId && !poll ? next.runs[0] : undefined);
        const linked = poll ? next.runs.filter((item) => item.poll_id === poll.run_id) : [];
        const ids = poll ? [poll.run_id, ...linked.map((item) => item.run_id)] : run ? [run.run_id] : [];
        const events = await Promise.all(ids.map((id) => dashboardApi.getDeliveryActivity(workspaceId, id)));
        if (cancelled) return;
        setActivity(events.flat().sort((a, b) => a.at.localeCompare(b.at)).slice(-200));
        setNow(Date.now());
      } catch (reason: unknown) {
        if (!cancelled) onError(reason instanceof ApiError ? reason.message : t("app.dashboardRequestFailed"));
      } finally {
        if (!cancelled) {
          setLoading(false);
          timer = window.setTimeout(() => void load(), 3000);
        }
      }
    }
    void load();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [workspaceId, selectedId, refresh, onError, t, deleting]);

  const poll = history.polls.find((item) => item.run_id === selectedId) ?? (selectedId ? undefined : history.polls[0]);
  const run = history.runs.find((item) => item.run_id === selectedId)
    ?? (poll ? history.runs.find((item) => item.poll_id === poll.run_id) : !selectedId ? history.runs[0] : undefined);
  const current = run ?? poll;
  const phase = current?.state === "idle" ? "discover" : current?.phase === "publish" ? "handoff" : current?.phase ?? "discover";
  const stageIndex = stages.findIndex((stage) => stage === phase);
  const live = current?.state === "running" || poll?.state === "running";
  const hasRunning = history.runs.some((item) => item.state === "running") || history.polls.some((item) => item.state === "running");

  useEffect(() => {
    if (!hasRunning) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [hasRunning]);

  function timeLabel(timestamp: string): string {
    return new Date(timestamp).toLocaleString(locale, {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", year: "numeric",
    });
  }

  function select(runId: string | null): void {
    setActivity([]);
    setSelectedId(runId);
  }

  async function deleteHistory(item: DeliveryRun): Promise<void> {
    if (deleting !== null || !window.confirm(t("autoDelivery.deleteConfirm", { key: item.story_key }))) return;
    setDeleting(item.run_id);
    onError(null);
    try {
      await dashboardApi.deleteDeliveryHistory(workspaceId, item.run_id);
      setHistory((current) => ({ ...current, runs: current.runs.filter((run) => run.run_id !== item.run_id) }));
      if (selectedId === item.run_id) select(null);
    } catch (reason: unknown) {
      onError(reason instanceof ApiError && reason.status !== 404 ? reason.message : t("autoDelivery.deleteFailed"));
    } finally {
      setDeleting(null);
    }
  }

  return <>
    <section className="panel delivery-progress-panel" aria-label={t("autoDelivery.progress")}>
      <div className="panel-heading">
        <h2>{t("autoDelivery.progress")}</h2>
        <div className="panel-actions">
          {selectedId && <button className="button button-secondary" type="button" onClick={() => select(null)}>{t("autoDelivery.latest")}</button>}
          <button className="button button-secondary" type="button" aria-label={t("overview.refresh")} onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={15} />{t("overview.refresh")}</button>
        </div>
      </div>
      {loading ? <div className="loading-inline" role="status"><LoaderCircle size={18} className="spin" />{t("autoDelivery.loading")}</div>
        : current ? <div className="delivery-progress-body">
          <div className="delivery-facts">
            <div><span>{t("autoDelivery.story")}</span><strong className="delivery-progress-story">{run ? <><StoryLink run={run} /><span className="delivery-progress-story-title">{run.story_title}</span></> : t("autoDelivery.checking")}</strong></div>
            <div><span>{t("autoScan.status")}</span><DeliveryStatus state={current.state} /></div>
            <div><span>{t("autoScan.started")}</span><strong>{timeLabel(current.started_at)}</strong></div>
            <div><span>{t("autoScan.duration")}</span><strong>{duration(current, now)}</strong></div>
          </div>
          <ol className="delivery-stages" aria-label={t("autoDelivery.stages")}>
            {stages.map((stage, index) => {
              const complete = current.state === "completed" || index < stageIndex || (current.state === "idle" && index === 0);
              const active = index === stageIndex && current.state !== "idle";
              const running = active && current.state === "running";
              return <li key={stage} className={complete ? "is-complete" : active ? `is-active ${running ? "is-running" : ""} ${current.state === "failed" || current.state === "blocked" ? "is-failed" : ""}` : ""} aria-current={active ? "step" : undefined}>
                <span className="delivery-stage-marker">{complete ? <Check size={13} /> : running ? <LoaderCircle size={13} className="spin" aria-hidden="true" /> : index + 1}</span>
                <span>{t(`autoDelivery.stage.${stage}`)}</span>
              </li>;
            })}
          </ol>
          <p className="delivery-summary" role="status">{current.state === "idle" ? t("autoDelivery.noEligible") : current.detail || (run && run.reason) || t("autoDelivery.awaitingProgress")}</p>
          <details className="delivery-activity-details">
            <summary>{t("autoDelivery.activity")}{live && <span className="status-pill status-warning"><Clock3 size={11} />{t("autoDelivery.live")}</span>}</summary>
            <ol className="delivery-activity-list" aria-label={t("autoDelivery.activity")}>
              {activity.length ? activity.map((event, index) => <li key={`${event.at}-${index}`}>
                <time dateTime={event.at}>{timeLabel(event.at)}</time><span>{stageLabel(event.phase, t)}</span>
                <div className="delivery-event-content">
                  <p>{event.detail}</p>
                  {event.command ? <details className="delivery-command-details">
                    <summary>{t("autoDelivery.commandDetails")}</summary>
                    <pre><code>{event.command}</code></pre>
                    <dl>
                      {event.operation_id && <><dt>{t("autoDelivery.operationId")}</dt><dd>{event.operation_id}</dd></>}
                      {event.exit_code != null && <><dt>{t("autoDelivery.exitCode")}</dt><dd>{event.exit_code}</dd></>}
                    </dl>
                    <small className="muted">{t("autoDelivery.commandPrivacy")}</small>
                  </details> : event.detail.startsWith("command execution:") && <small className="muted">{t("autoDelivery.commandUnavailable")}</small>}
                </div>
              </li>) : <li className="muted">{t("autoDelivery.noActivity")}</li>}
            </ol>
          </details>
        </div> : <p className="delivery-empty">{t("autoDelivery.noProgress")}</p>}
    </section>

    <section className="panel" aria-label={t("autoDelivery.history")}>
      <div className="panel-heading"><h2>{t("autoDelivery.history")}</h2><span className="muted">{history.runs.length}</span></div>
      <div className="table-scroll scan-history-scroll" tabIndex={0} role="region" aria-label={t("autoDelivery.history")}>
        <table className="scan-history-table delivery-history-table">
          <thead><tr><th scope="col">{t("autoDelivery.story")}</th><th scope="col">{t("autoScan.started")}</th><th scope="col">{t("autoScan.status")}</th><th scope="col">{t("autoScan.duration")}</th><th scope="col">{t("autoDelivery.actions")}</th></tr></thead>
          <tbody>{history.runs.length ? history.runs.map((item) => <tr key={item.run_id}>
            <td className="delivery-story-cell"><div className="delivery-story-line"><StoryLink run={item} /><span className="delivery-story-title" title={item.story_title}>{item.story_title}</span></div>{item.branch && <small className="muted delivery-story-branch">{item.branch}</small>}</td>
            <td>{timeLabel(item.started_at)}</td>
            <td><button type="button" className="delivery-inspect" aria-label={`${t("autoDelivery.inspect")} ${item.story_key}`} onClick={() => select(item.run_id)}><DeliveryStatus state={item.state} /></button></td>
            <td>{duration(item, now)}</td>
            <td><button className="button button-secondary delivery-history-delete" type="button" aria-label={`${t("autoDelivery.delete")} ${item.story_key}`} disabled={deleting !== null || item.state === "running" || history.polls.some((poll) => poll.state === "running")} onClick={() => void deleteHistory(item)}>
              {deleting === item.run_id ? <LoaderCircle size={14} className="spin" /> : <Trash2 size={14} />}{t("autoDelivery.delete")}
            </button></td>
          </tr>) : <tr><td colSpan={5} className="empty-table">{t("autoDelivery.noHistory")}</td></tr>}</tbody>
        </table>
      </div>
    </section>

    <section className="panel" aria-label={t("autoDelivery.schedulerActivity")}>
      <div className="panel-heading"><h2>{t("autoDelivery.schedulerActivity")}</h2></div>
      <div className="table-scroll scan-history-scroll" tabIndex={0} role="region" aria-label={t("autoDelivery.schedulerActivity")}>
        <table className="scan-history-table delivery-history-table">
          <thead><tr><th scope="col">{t("autoScan.started")}</th><th scope="col">{t("autoScan.status")}</th><th scope="col">{t("autoScan.duration")}</th></tr></thead>
          <tbody>{history.polls.length ? history.polls.map((item) => <tr key={item.run_id}>
            <td>{timeLabel(item.started_at)}</td><td><button className="delivery-inspect" type="button" aria-label={`${t("autoDelivery.inspect")} ${timeLabel(item.started_at)}`} onClick={() => select(item.run_id)}><DeliveryStatus state={item.state} /></button></td>
            <td>{duration(item, now)}</td>
          </tr>) : <tr><td colSpan={3} className="empty-table">{t("autoDelivery.noActivity")}</td></tr>}</tbody>
        </table>
      </div>
    </section>
  </>;
}

function StoryLink({ run }: { run: DeliveryRun }): React.JSX.Element {
  return run.jira_url ? <a href={run.jira_url} target="_blank" rel="noreferrer">{run.story_key}<ExternalLink size={12} /></a> : <span>{run.story_key}</span>;
}

function DeliveryStatus({ state }: { state: DeliveryRun["state"] | DeliveryPoll["state"] }): React.JSX.Element {
  const { t } = useI18n();
  const tone = state === "completed" ? "ready" : state === "failed" ? "danger" : state === "idle" ? "neutral" : "warning";
  return <span className={`status-pill status-${tone}`}>{t(`autoDelivery.status.${state}`)}</span>;
}

function stageLabel(phase: string, t: Translator): string {
  const stage = stages.find((value) => value === (phase === "publish" ? "handoff" : phase));
  return stage ? t(`autoDelivery.stage.${stage}`) : phase;
}

function duration(run: DeliveryRun | DeliveryPoll, now: number): string {
  const seconds = run.state === "running" ? Math.max(0, Math.floor((now - Date.parse(run.started_at)) / 1000)) : run.duration_seconds;
  return seconds === null ? "—" : `${Math.floor(seconds / 60)}m${seconds % 60}s`;
}
