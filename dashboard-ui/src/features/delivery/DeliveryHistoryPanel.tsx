import { Check, Clock3, LoaderCircle, RefreshCw, RotateCcw, Trash2, Play, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { ApiError, dashboardApi } from "../../app/api";
import { useI18n, type Translator } from "../../shared/i18n";
import type { DeliveryActivity, DeliveryHistory, DeliveryPoll, DeliveryRun } from "../../shared/types";
import { DeliveryRework, deliveryReworks } from "./DeliveryRework";

const stages = ["discover", "claim", "implementation", "verification", "handoff"] as const;

export function DeliveryHistoryPanel({ workspaceId, onError }: {
  workspaceId: string; onError: (message: string | null) => void;
}): React.JSX.Element {
  const { locale, t } = useI18n();
  const [history, setHistory] = useState<DeliveryHistory>({ runs: [], polls: [] });
  const [activities, setActivities] = useState<Record<string, DeliveryActivity[]>>({});
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(Date.now());
  const [deleting, setDeleting] = useState<string | null>(null);
  const [controlling, setControlling] = useState<string | null>(null);

  useEffect(() => {
    if (deleting !== null || controlling !== null) return;
    let cancelled = false;
    let timer: number | undefined;
    async function load(): Promise<void> {
      try {
        const next = await dashboardApi.getDeliveryHistory(workspaceId);
        if (cancelled) return;
        setHistory(next);
        setNow(Date.now());
        const run = latestDeliveryRun(next.runs);
        const inspected = [...next.runs, ...next.polls].find((item) => item.run_id === selectedId);
        const ids = [...new Set([run?.run_id, inspected?.run_id].filter((id): id is string => Boolean(id)))];
        const events = await Promise.all(ids.map(async (id) => [
          id, (await dashboardApi.getDeliveryActivity(workspaceId, id)).sort((a, b) => a.at.localeCompare(b.at)).slice(-200),
        ] as const));
        if (cancelled) return;
        setActivities(Object.fromEntries(events));
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
  }, [workspaceId, selectedId, refresh, onError, t, deleting, controlling]);

  const current = latestDeliveryRun(history.runs);
  const inspectedRun = history.runs.find((item) => item.run_id === selectedId);
  const inspectedPoll = history.polls.find((item) => item.run_id === selectedId);
  const phase = current?.phase === "publish" ? "handoff" : current?.phase ?? "discover";
  const stageIndex = stages.findIndex((stage) => stage === phase);
  const reworks = deliveryReworks(current ? activities[current.run_id] ?? [] : []);
  const live = current?.state === "running";
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
    setSelectedId(runId);
  }

  async function control(item: DeliveryRun, action: "resume" | "stop"): Promise<void> {
    if (controlling !== null || !window.confirm(t(`autoDelivery.${action}Confirm`, { key: item.story_key }))) return;
    setControlling(item.run_id);
    onError(null);
    try {
      await dashboardApi.controlDelivery(workspaceId, item.run_id, action, item.attempt ?? 1);
      setRefresh((value) => value + 1);
    } catch (reason: unknown) {
      onError(reason instanceof ApiError ? reason.message : t("app.dashboardRequestFailed"));
    } finally {
      setControlling(null);
    }
  }

  function controlButton(item: DeliveryRun): React.JSX.Element | null {
    const action = item.state === "running" ? "stop" : "resume";
    if (item.state === "completed" || (action === "stop" && item.stopping == null)) return null;
    return <button className="button button-secondary" type="button" disabled={controlling !== null || deleting !== null || Boolean(item.stopping) || (action === "resume" && hasRunning)} onClick={() => void control(item, action)}>
      {controlling === item.run_id || item.stopping ? <LoaderCircle size={14} className="spin" /> : action === "stop" ? <Square size={14} /> : <Play size={14} />}
      {t(item.stopping ? "autoDelivery.stopping" : `autoDelivery.${action}`)}
    </button>;
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
          {current && controlButton(current)}
          <button className="button button-secondary" type="button" aria-label={t("overview.refresh")} onClick={() => setRefresh((value) => value + 1)}><RefreshCw size={15} />{t("overview.refresh")}</button>
        </div>
      </div>
      {loading ? <div className="loading-inline" role="status"><LoaderCircle size={18} className="spin" />{t("autoDelivery.loading")}</div>
        : current ? <div className="delivery-progress-body">
          <div className="delivery-facts">
            <div><span>{t("autoDelivery.story")}</span><strong><StoryLink run={current} className="delivery-progress-story" /></strong></div>
            <div><span>{t("autoScan.status")}</span><DeliveryStatus state={current.state} /></div>
            <div><span>{t("autoScan.started")}</span><strong>{timeLabel(current.started_at)}</strong></div>
            <div><span>{t("autoDelivery.attempt", { count: current.attempt ?? 1 })}</span><strong>{duration(current, now)}</strong></div>
          </div>
          <ol className="delivery-stages" aria-label={t("autoDelivery.stages")}>
            {stages.map((stage, index) => {
              const complete = current.state === "completed" || index < stageIndex;
              const active = index === stageIndex && current.state !== "completed";
              const running = active && current.state === "running";
              const returned = stage === "verification" && phase === "implementation" && reworks.length > 0 && live;
              return <li key={stage} className={complete ? "is-complete" : active ? `is-active ${running ? "is-running" : ""} ${current.state === "failed" || current.state === "blocked" ? "is-failed" : ""}` : returned ? "is-returned" : ""} aria-current={active ? "step" : undefined}>
                <span className="delivery-stage-marker">{complete ? <Check size={13} /> : running ? <LoaderCircle size={13} className="spin" aria-hidden="true" /> : returned ? <RotateCcw size={13} aria-hidden="true" /> : index + 1}</span>
                <span>{t(`autoDelivery.stage.${stage}`)}</span>
              </li>;
            })}
          </ol>
          <DeliveryRework run={current} reworks={reworks} timeLabel={timeLabel} />
          <DeliveryActivityDetails activity={activities[current.run_id] ?? []} live={live} timeLabel={timeLabel} />
        </div> : <p className="delivery-empty">{t("autoDelivery.noProgress")}</p>}
    </section>

    <section className="panel" aria-label={t("autoDelivery.history")}>
      <div className="panel-heading"><h2>{t("autoDelivery.history")}</h2><span className="muted">{history.runs.length}</span></div>
      <div className="table-scroll scan-history-scroll delivery-history-scroll" tabIndex={0} role="region" aria-label={t("autoDelivery.history")}>
        <table className="scan-history-table delivery-history-table">
          <thead><tr><th scope="col">{t("autoDelivery.story")}</th><th scope="col">{t("autoScan.started")}</th><th scope="col">{t("autoScan.status")}</th><th scope="col">{t("autoScan.duration")}</th><th scope="col">{t("autoDelivery.actions")}</th></tr></thead>
          <tbody>{history.runs.length ? history.runs.map((item) => <tr key={item.run_id}>
            <td className="delivery-story-cell"><StoryLink run={item} className="delivery-story-line" /><small className="muted delivery-story-metadata">{item.story_key}</small></td>
            <td>{timeLabel(item.started_at)}</td>
            <td><button type="button" className="delivery-inspect" aria-label={`${t("autoDelivery.inspect")} ${item.story_key}`} onClick={() => select(item.run_id)}><DeliveryStatus state={item.state} /></button></td>
            <td>{duration(item, now)}</td>
            <td><div className="panel-actions">{item.state !== "running" && controlButton(item)}<button className="button button-secondary delivery-history-delete" type="button" aria-label={`${t("autoDelivery.delete")} ${item.story_key}`} disabled={deleting !== null || controlling !== null || item.state === "running" || history.polls.some((poll) => poll.state === "running")} onClick={() => void deleteHistory(item)}>
              {deleting === item.run_id ? <LoaderCircle size={14} className="spin" /> : <Trash2 size={14} />}{t("autoDelivery.delete")}
            </button></div></td>
          </tr>) : <tr><td colSpan={5} className="empty-table">{t("autoDelivery.noHistory")}</td></tr>}</tbody>
        </table>
      </div>
      {inspectedRun && <DeliveryInspection run={inspectedRun} activity={activities[inspectedRun.run_id] ?? []} timeLabel={timeLabel} onClose={() => select(null)} />}
    </section>

    <section className="panel" aria-label={t("autoDelivery.schedulerActivity")}>
      <div className="panel-heading"><h2>{t("autoDelivery.schedulerActivity")}</h2></div>
      <div className="table-scroll scan-history-scroll delivery-history-scroll" tabIndex={0} role="region" aria-label={t("autoDelivery.schedulerActivity")}>
        <table className="scan-history-table delivery-history-table">
          <thead><tr><th scope="col">{t("autoScan.started")}</th><th scope="col">{t("autoScan.status")}</th><th scope="col">{t("autoScan.duration")}</th></tr></thead>
          <tbody>{history.polls.length ? history.polls.map((item) => <tr key={item.run_id}>
            <td>{timeLabel(item.started_at)}</td><td><button className="delivery-inspect" type="button" aria-label={`${t("autoDelivery.inspect")} ${timeLabel(item.started_at)}`} onClick={() => select(item.run_id)}><DeliveryStatus state={item.state} /></button></td>
            <td>{duration(item, now)}</td>
          </tr>) : <tr><td colSpan={3} className="empty-table">{t("autoDelivery.noActivity")}</td></tr>}</tbody>
        </table>
      </div>
      {inspectedPoll && <DeliveryInspection run={inspectedPoll} activity={activities[inspectedPoll.run_id] ?? []} timeLabel={timeLabel} onClose={() => select(null)} />}
    </section>
  </>;
}

function latestDeliveryRun(runs: DeliveryRun[]): DeliveryRun | undefined {
  const latest = [...runs].sort((a, b) => Date.parse(b.attempt_started_at ?? b.started_at) - Date.parse(a.attempt_started_at ?? a.started_at));
  return latest.find((run) => run.state === "running") ?? latest[0];
}

function DeliveryInspection({ run, activity, timeLabel, onClose }: {
  run: DeliveryRun | DeliveryPoll; activity: DeliveryActivity[];
  timeLabel: (timestamp: string) => string; onClose: () => void;
}): React.JSX.Element {
  const { t } = useI18n();
  return <div className="delivery-inspection">
    <div className="panel-heading">
      <strong>{"story_key" in run ? <StoryLink run={run} className="delivery-progress-story" /> : timeLabel(run.started_at)}</strong>
      <button className="button button-secondary" type="button" onClick={onClose}>{t("app.close")}</button>
    </div>
    <div className="delivery-progress-body">
      {"story_key" in run && <DeliveryRework run={run} reworks={deliveryReworks(activity)} timeLabel={timeLabel} />}
      <DeliveryActivityDetails activity={activity} live={run.state === "running"} timeLabel={timeLabel} />
    </div>
  </div>;
}

function DeliveryActivityDetails({ activity, live, timeLabel }: {
  activity: DeliveryActivity[]; live: boolean; timeLabel: (timestamp: string) => string;
}): React.JSX.Element {
  const { t } = useI18n();
  return <details className="delivery-activity-details">
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
  </details>;
}

function StoryLink({ run, className }: {
  run: DeliveryRun; className: string;
}): React.JSX.Element {
  const label = `[${run.story_key}] ${run.story_title}`;
  return run.jira_url ? <a className={className} title={label} href={run.jira_url} target="_blank" rel="noreferrer">{label}</a> : <span className={className} title={label}>{label}</span>;
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
  const startedAt = "attempt_started_at" in run ? run.attempt_started_at ?? run.started_at : run.started_at;
  const seconds = run.state === "running" ? Math.max(0, Math.floor((now - Date.parse(startedAt)) / 1000)) : run.duration_seconds;
  return seconds === null ? "—" : `${Math.floor(seconds / 60)}m${seconds % 60}s`;
}
