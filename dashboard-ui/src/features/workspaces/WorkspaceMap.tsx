import { ArrowRight, Bot, FolderGit2, GitBranch, Puzzle, Rocket, ScanSearch } from "lucide-react";
import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
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

export function WorkspaceMap({ overview, settings, agentSettings, onNavigate, onOpenWorkflow }: WorkspaceMapProps): React.JSX.Element {
  const { t } = useI18n();
  const [catalogs, setCatalogs] = useState<Catalogs | null>(null);
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
  const documentState = (document: CapabilitySummary | FlowSummary): string => !document.valid
    ? t("map.invalid") : stateLabel(document.enabled);
  const activeCount = (documents: (CapabilitySummary | FlowSummary)[]): string => t("map.available", {
    enabled: documents.filter((document) => document.valid && document.enabled).length,
    total: documents.length,
  });

  return (
    <figure className="workspace-map" aria-labelledby="workspace-map-title">
      <header className="workspace-map-heading">
        <h2 id="workspace-map-title">{t("map.title")}</h2>
      </header>
      <div className="workspace-map-diagram">
        <section className="workspace-map-context" aria-labelledby="map-capabilities-title">
          <div className="workspace-map-node-heading"><Puzzle size={17} /><h3 id="map-capabilities-title">{t("app.capabilities")}</h3><button type="button" onClick={() => onNavigate("capabilities")} aria-label={t("map.manageCapabilities")}><ArrowRight size={15} /></button></div>
          <p className="workspace-map-count">{current?.capabilitiesFailed ? t("map.loadFailed") : capabilities ? activeCount(capabilities) : t("map.loading")}</p>
          {capabilities && (capabilities.length ? <ul className="workspace-map-catalog" tabIndex={0} aria-label={t("app.capabilities")}>
            {capabilities.map((capability) => {
              const description = capability.brief.trim();
              return <li key={capability.capability_id} title={description || undefined}>
                <span>{capability.name}</span><small className={!capability.valid ? "map-state-invalid" : capability.enabled ? "map-state-enabled" : "map-state-disabled"}>{documentState(capability)}</small>
                <p className="workspace-map-description">{description || t("map.noDescription")}</p>
              </li>;
            })}
          </ul> : <p className="workspace-map-empty">{t("map.noCapabilities")}</p>)}
        </section>

        <div className="workspace-map-connector" aria-hidden="true"><svg viewBox="0 0 36 12"><path d="M0 6H36" /></svg></div>

        <div className="workspace-map-hub-position">
          <span aria-hidden="true" />
          <button className="workspace-map-hub" type="button" onClick={() => onNavigate("settings")} aria-label={t("overview.details")}>
            <FolderGit2 size={24} />
            <span>{t("app.workspaceGroup")}</span>
            <strong>{overview.name}</strong>
            <small>{overview.repositories.length} {t("overview.repositories")}</small>
          </button>
          <span className="workspace-map-hub-stem" aria-hidden="true" />
        </div>

        <div className="workspace-map-connector" aria-hidden="true"><svg viewBox="0 0 36 12"><path d="M0 6H36" /></svg></div>

        <section className="workspace-map-workflows" aria-labelledby="map-workflows-title">
          <div className="workspace-map-workflow-heading"><GitBranch size={17} /><h3 id="map-workflows-title">{t("app.flows")}</h3><button type="button" onClick={() => onNavigate("flows")} aria-label={t("map.browseWorkflows")}><ArrowRight size={15} /></button></div>
          <p className="workspace-map-count">{current?.flowsFailed ? t("map.loadFailed") : flows ? activeCount(flows) : t("map.loading")}</p>
          {flows && (flows.length ? <ul className="workspace-map-flow-list" tabIndex={0} aria-label={t("app.flows")}>
            {flows.map((flow) => {
              const schedule = overview.workflow_schedules.find((item) => item.flow_id === flow.flow_id);
              const description = flow.brief.trim();
              return <li key={flow.flow_id}><button type="button" onClick={() => onOpenWorkflow(flow.flow_id)} title={description || undefined}>
                <strong>{flow.name}</strong><small className={!flow.valid ? "map-state-invalid" : flow.enabled ? "map-state-enabled" : "map-state-disabled"}>{documentState(flow)}</small>
                <p className="workspace-map-description">{description || t("map.noDescription")}</p>
                {schedule && <code>{t(schedule.enabled ? "map.scheduled" : "map.schedulePaused")} · {schedule.schedule_expression}</code>}
              </button></li>;
            })}
          </ul> : <p className="workspace-map-empty">{t("map.noWorkflows")}</p>)}
        </section>
      </div>

      <section className="workspace-map-execution" aria-label={t("map.execution")}>
        <div className="workspace-map-lanes">
          <button className="workspace-map-node workspace-map-agent" type="button" onClick={() => onNavigate("agent")}>
            <div className="workspace-map-node-heading"><Bot size={19} /><h4>{t("app.agentSettings")}</h4><span className="workspace-map-state">{stateLabel(agentSettings?.enabled)}</span></div>
            <code>{agentSettings ? `${agentSettings.agent_model} · ${agentSettings.agent_reasoning_effort}` : t("map.unknown")}</code>
            {agentSettings && agentSettings.default_workspace_id !== overview.workspace_id && <small>{t("map.notDefault")}</small>}
          </button>
          <button className="workspace-map-node" type="button" onClick={() => onNavigate("auto-scan")}>
            <div className="workspace-map-node-heading"><ScanSearch size={18} /><h4>{t("app.autoScan")}</h4><span className="workspace-map-state">{stateLabel(currentSettings?.auto_scan.enabled)}</span></div>
            <code>{currentSettings ? currentSettings.auto_scan.schedule_expression || t("overview.unscheduled") : t("map.unknown")}</code>
          </button>
          <button className="workspace-map-node" type="button" onClick={() => onNavigate("auto-delivery")}>
            <div className="workspace-map-node-heading"><Rocket size={18} /><h4>{t("app.autoDelivery")}</h4><span className="workspace-map-state">{stateLabel(currentSettings?.auto_delivery.enabled)}</span></div>
            <code>{currentSettings ? currentSettings.auto_delivery.schedule_expression || t("overview.unscheduled") : t("map.unknown")}</code>
          </button>
        </div>
      </section>
    </figure>
  );
}
