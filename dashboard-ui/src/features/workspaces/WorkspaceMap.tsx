import { ArrowRight, Bot, FolderGit2, GitBranch, Puzzle, Rocket, ScanSearch, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n, type Translator } from "../../shared/i18n";
import type { AgentSettings, CapabilitySummary, FlowSummary, View, WorkspaceOverview, WorkspaceSettings } from "../../shared/types";
import "./WorkspaceMap.css";

interface WorkspaceMapProps {
  overview: WorkspaceOverview;
  settings: WorkspaceSettings | null;
  agentSettings: AgentSettings | null;
  onNavigate: (view: View) => void;
  onOpenWorkflow: (flowId: string) => void;
}

interface Catalogs {
  workspaceId: string;
  capabilities: CapabilitySummary[] | null;
  flows: FlowSummary[] | null;
  capabilitiesFailed: boolean;
  flowsFailed: boolean;
}

type MapFilter = "all" | "capabilities" | "workflows" | "execution";
type Selection = { type: "workspace" | "agent" | "scan" | "delivery" }
  | { type: "capability" | "workflow"; id: string };

interface MapDetail {
  name: string;
  status: string;
  description?: string;
  rows?: { label: string; value: string }[];
  actionLabel: string;
  onAction: () => void;
}

function formatSchedule(expression: string, t: Translator): string {
  const cron = expression.trim();
  if (!cron) return t("overview.unscheduled");
  const minutes = /^\*\/(\d+) \* \* \* \*$/.exec(cron);
  if (minutes) {
    const interval = Number(minutes[1]);
    if (interval === 1) return t("map.everyMinute");
    if (interval > 1 && interval < 60 && 60 % interval === 0) return t("map.everyMinutes", { count: interval });
  }
  const weekdays = /^(\d{1,2}) (\d{1,2}) \* \* 1-5$/.exec(cron);
  if (weekdays && Number(weekdays[1]) < 60 && Number(weekdays[2]) < 24) {
    return t("map.weekdaysAt", { time: `${weekdays[2].padStart(2, "0")}:${weekdays[1].padStart(2, "0")}` });
  }
  return cron;
}

function MapDialog({ detail, onClose }: { detail: MapDetail; onClose: () => void }): React.JSX.Element {
  const { t } = useI18n();
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    return () => {
      if (dialog.open && typeof dialog.close === "function") dialog.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return <dialog ref={ref} className="workspace-map-dialog" aria-labelledby="workspace-map-dialog-title"
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <header className="workspace-map-dialog-heading">
      <h3 id="workspace-map-dialog-title">{detail.name}</h3>
      <button type="button" className="workspace-map-dialog-close" aria-label={t("app.close")} onClick={onClose} autoFocus><X size={16} /></button>
    </header>
    <div className="workspace-map-dialog-body">
      {detail.description && <p>{detail.description}</p>}
      <dl>
        <div><dt>{t("autoScan.status")}</dt><dd>{detail.status}</dd></div>
        {detail.rows?.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}
      </dl>
      <button type="button" className="button button-secondary workspace-map-dialog-action" onClick={() => { onClose(); detail.onAction(); }}>
        {detail.actionLabel}<ArrowRight size={15} />
      </button>
    </div>
  </dialog>;
}

export function WorkspaceMap({ overview, settings, agentSettings, onNavigate, onOpenWorkflow }: WorkspaceMapProps): React.JSX.Element {
  const { t } = useI18n();
  const [catalogs, setCatalogs] = useState<Catalogs | null>(null);
  const [filter, setFilter] = useState<MapFilter>("all");
  const [selection, setSelection] = useState<Selection | null>(null);
  useEffect(() => {
    setSelection(null);
    setFilter("all");
  }, [overview.workspace_id]);
  useEffect(() => {
    let cancelled = false;
    let inFlight = false;
    let timer: number | undefined;
    const clearTimer = (): void => { window.clearTimeout(timer); };
    async function refreshCatalogs(): Promise<void> {
      if (cancelled || inFlight || document.visibilityState !== "visible") return;
      inFlight = true;
      const [capabilities, flows] = await Promise.allSettled([
        dashboardApi.listCapabilities(overview.workspace_id),
        dashboardApi.listFlows(overview.workspace_id),
      ]);
      inFlight = false;
      if (cancelled || document.visibilityState !== "visible") return;
      setCatalogs((previous) => {
        const saved = previous?.workspaceId === overview.workspace_id ? previous : null;
        return {
          workspaceId: overview.workspace_id,
          capabilities: capabilities.status === "fulfilled" ? capabilities.value : saved?.capabilities ?? null,
          flows: flows.status === "fulfilled" ? flows.value : saved?.flows ?? null,
          capabilitiesFailed: capabilities.status === "rejected",
          flowsFailed: flows.status === "rejected",
        };
      });
      timer = window.setTimeout(() => void refreshCatalogs(), 15_000);
    }
    function onVisibilityChange(): void {
      clearTimer();
      if (document.visibilityState === "visible") void refreshCatalogs();
    }
    document.addEventListener("visibilitychange", onVisibilityChange);
    void refreshCatalogs();
    return () => {
      cancelled = true;
      clearTimer();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [overview]);

  const current = catalogs?.workspaceId === overview.workspace_id ? catalogs : null;
  const capabilities = current?.capabilities;
  const flows = current?.flows;
  const currentSettings = settings?.workspace_id === overview.workspace_id ? settings : null;
  const stateLabel = (enabled: boolean | undefined): string => enabled === undefined
    ? t("map.unknown") : enabled ? t("settings.enabled") : t("settings.disabled");
  const enabledClass = (enabled: boolean | undefined): string => enabled === undefined
    ? "unknown" : enabled ? "enabled" : "disabled";
  const documentState = (document: CapabilitySummary | FlowSummary): string => !document.valid
    ? t("map.invalid") : stateLabel(document.enabled);
  const stateClass = (document: CapabilitySummary | FlowSummary): string => !document.valid
    ? "invalid" : document.enabled ? "enabled" : "disabled";
  const activeCount = (documents: (CapabilitySummary | FlowSummary)[]): string => t("map.count", {
    enabled: documents.filter((document) => document.valid && document.enabled).length,
    total: documents.length,
  });
  const scheduleText = (expression: string | undefined): string => expression === undefined
    ? t("map.unknown") : formatSchedule(expression, t);

  let detail: MapDetail | null = null;
  if (selection?.type === "capability") {
    const capability = capabilities?.find((item) => item.capability_id === selection.id);
    if (capability) detail = {
      name: capability.name, status: documentState(capability), description: capability.brief.trim() || t("map.noDescription"),
      actionLabel: t("map.manageCapabilities"), onAction: () => onNavigate("capabilities"),
    };
  } else if (selection?.type === "workflow") {
    const flow = flows?.find((item) => item.flow_id === selection.id);
    const schedule = overview.workflow_schedules.find((item) => item.flow_id === selection.id);
    if (flow) detail = {
      name: flow.name, status: documentState(flow), description: flow.brief.trim() || t("map.noDescription"),
      rows: schedule ? [{ label: t("flows.scheduleTitle"), value: `${t(schedule.enabled ? "map.scheduled" : "map.schedulePaused")} · ${schedule.schedule_expression}` }] : [],
      actionLabel: t("map.openWorkflow"), onAction: () => onOpenWorkflow(flow.flow_id),
    };
  } else if (selection?.type === "workspace") {
    detail = { name: overview.name, status: t("overview.initialized"), rows: [{ label: t("overview.id"), value: overview.workspace_id }],
      actionLabel: t("app.settings"), onAction: () => onNavigate("settings") };
  } else if (selection?.type === "agent") {
    detail = { name: t("app.agentSettings"), status: stateLabel(agentSettings?.enabled),
      description: agentSettings && agentSettings.default_workspace_id !== overview.workspace_id ? t("map.notDefault") : undefined,
      rows: agentSettings ? [{ label: t("map.modelEffort"), value: `${agentSettings.agent_model} · ${agentSettings.agent_reasoning_effort}` }] : [],
      actionLabel: t("app.agentSettings"), onAction: () => onNavigate("agent") };
  } else if (selection?.type === "scan" || selection?.type === "delivery") {
    const isScan = selection.type === "scan";
    const config = isScan ? currentSettings?.auto_scan : currentSettings?.auto_delivery;
    const view = isScan ? "auto-scan" : "auto-delivery";
    detail = { name: t(isScan ? "app.autoScan" : "app.autoDelivery"), status: stateLabel(config?.enabled),
      rows: [{ label: t("flows.scheduleTitle"), value: config?.schedule_expression || (config ? t("overview.unscheduled") : t("map.unknown")) }],
      actionLabel: t(isScan ? "app.autoScan" : "app.autoDelivery"), onAction: () => onNavigate(view) };
  }
  useEffect(() => { if (selection && !detail) setSelection(null); }, [selection, detail]);

  const filters: { value: MapFilter; label: string }[] = [
    { value: "all", label: t("map.filterAll") },
    { value: "capabilities", label: t("map.filterCapabilities") },
    { value: "workflows", label: t("map.filterWorkflows") },
    { value: "execution", label: t("map.filterExecution") },
  ];
  return (
    <figure className="workspace-map" aria-labelledby="workspace-map-title">
      <header className="workspace-map-heading">
        <div className="workspace-map-title"><span className="workspace-map-title-icon"><GitBranch size={18} /></span><h2 id="workspace-map-title">{t("map.title")}</h2></div>
        <div className="workspace-map-filters" role="group" aria-label={t("map.filterLabel")}>
          {filters.map((item) => <button key={item.value} type="button" aria-pressed={filter === item.value} onClick={() => setFilter(item.value)}>{item.label}</button>)}
        </div>
      </header>
      <div className="workspace-map-body" data-focus={filter}>
        <div className="workspace-map-diagram">
          <section className="workspace-map-context" aria-labelledby="map-capabilities-title">
            <div className="workspace-map-panel-heading">
              <h3 id="map-capabilities-title" className="workspace-map-panel-title" aria-label={t("app.capabilities")}><button type="button" onClick={() => onNavigate("capabilities")} aria-label={t("map.manageCapabilities")}>
                <span className="workspace-map-panel-icon capability"><Puzzle size={16} /></span><span>{t("app.capabilities")}</span>
              </button></h3>
              <span className={`workspace-map-count${current?.capabilitiesFailed ? " is-error" : ""}`} aria-live="polite">{current?.capabilitiesFailed ? t("map.loadFailed") : capabilities ? activeCount(capabilities) : t("map.loading")}</span>
            </div>
            {capabilities && (capabilities.length ? <ul className="workspace-map-catalog" aria-label={t("app.capabilities")}>
              {capabilities.map((capability) => <li key={capability.capability_id}><button type="button" onClick={() => setSelection({ type: "capability", id: capability.capability_id })}>
                <strong>{capability.name}</strong><span className={`workspace-map-dot ${stateClass(capability)}`} aria-hidden="true" /><span className="sr-only">{documentState(capability)}</span><ArrowRight className="workspace-map-row-arrow" size={14} aria-hidden="true" />
              </button></li>)}
            </ul> : <p className="workspace-map-empty">{t("map.noCapabilities")}</p>)}
          </section>
          <div className="workspace-map-connector" aria-hidden="true"><svg viewBox="0 0 36 12"><path d="M0 6H36" /></svg></div>
          <div className="workspace-map-hub-position">
            <span aria-hidden="true" />
            <button className="workspace-map-hub" type="button" onClick={() => setSelection({ type: "workspace" })} aria-label={t("overview.details")}>
              <span className="workspace-map-hub-icon"><FolderGit2 size={20} /></span><strong>{overview.name}</strong>
              <small><GitBranch size={12} />{overview.repositories.length} {t("overview.repositories")}</small>
            </button>
            <span className="workspace-map-hub-stem" aria-hidden="true" />
          </div>
          <div className="workspace-map-connector" aria-hidden="true"><svg viewBox="0 0 36 12"><path d="M0 6H36" /></svg></div>
          <section className="workspace-map-workflows" aria-labelledby="map-workflows-title">
            <div className="workspace-map-panel-heading">
              <h3 id="map-workflows-title" className="workspace-map-panel-title" aria-label={t("app.flows")}><button type="button" onClick={() => onNavigate("flows")} aria-label={t("map.browseWorkflows")}>
                <span className="workspace-map-panel-icon workflow"><GitBranch size={16} /></span><span>{t("app.flows")}</span>
              </button></h3>
              <span className={`workspace-map-count${current?.flowsFailed ? " is-error" : ""}`} aria-live="polite">{current?.flowsFailed ? t("map.loadFailed") : flows ? activeCount(flows) : t("map.loading")}</span>
            </div>
            {flows && (flows.length ? <ul className="workspace-map-flow-list" aria-label={t("app.flows")}>
              {flows.map((flow) => {
                const schedule = overview.workflow_schedules.find((item) => item.flow_id === flow.flow_id);
                return <li key={flow.flow_id}><button type="button" onClick={() => setSelection({ type: "workflow", id: flow.flow_id })}>
                  <span className="workspace-map-row-copy"><strong>{flow.name}</strong>{schedule && <small>{!schedule.enabled && `${t("map.schedulePaused")} · `}{scheduleText(schedule.schedule_expression)}</small>}</span>
                  <span className={`workspace-map-dot ${stateClass(flow)}`} aria-hidden="true" /><span className="sr-only">{documentState(flow)}</span><ArrowRight className="workspace-map-row-arrow" size={14} aria-hidden="true" />
                </button></li>;
              })}
            </ul> : <p className="workspace-map-empty">{t("map.noWorkflows")}</p>)}
          </section>
        </div>
        <section className="workspace-map-execution" aria-label={t("map.execution")}>
          <div className="workspace-map-lanes">
            <button className="workspace-map-node" type="button" onClick={() => setSelection({ type: "agent" })}>
              <span className="workspace-map-exec-icon agent"><Bot size={17} /></span><span className="workspace-map-node-copy"><strong>{t("app.agentSettings")}</strong><small>{agentSettings ? `${agentSettings.agent_model} · ${agentSettings.agent_reasoning_effort}` : t("map.unknown")}</small></span>
              <span className={`workspace-map-state ${enabledClass(agentSettings?.enabled)}`}><span className={`workspace-map-dot ${enabledClass(agentSettings?.enabled)}`} aria-hidden="true" />{stateLabel(agentSettings?.enabled)}</span>
            </button>
            <button className="workspace-map-node" type="button" onClick={() => setSelection({ type: "scan" })}>
              <span className="workspace-map-exec-icon scan"><ScanSearch size={17} /></span><span className="workspace-map-node-copy"><strong>{t("app.autoScan")}</strong><small>{scheduleText(currentSettings?.auto_scan.schedule_expression)}</small></span>
              <span className={`workspace-map-state ${enabledClass(currentSettings?.auto_scan.enabled)}`}><span className={`workspace-map-dot ${enabledClass(currentSettings?.auto_scan.enabled)}`} aria-hidden="true" />{stateLabel(currentSettings?.auto_scan.enabled)}</span>
            </button>
            <button className="workspace-map-node" type="button" onClick={() => setSelection({ type: "delivery" })}>
              <span className="workspace-map-exec-icon delivery"><Rocket size={17} /></span><span className="workspace-map-node-copy"><strong>{t("app.autoDelivery")}</strong><small>{scheduleText(currentSettings?.auto_delivery.schedule_expression)}</small></span>
              <span className={`workspace-map-state ${enabledClass(currentSettings?.auto_delivery.enabled)}`}><span className={`workspace-map-dot ${enabledClass(currentSettings?.auto_delivery.enabled)}`} aria-hidden="true" />{stateLabel(currentSettings?.auto_delivery.enabled)}</span>
            </button>
          </div>
        </section>
      </div>
      {detail && <MapDialog detail={detail} onClose={() => setSelection(null)} />}
    </figure>
  );
}
