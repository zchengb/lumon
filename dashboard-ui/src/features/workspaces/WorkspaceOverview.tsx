import { ArrowUpRight, Bot, CheckCircle2, Clock3, FolderGit2, GitBranch, HardDrive, Puzzle, RefreshCw, Rocket, ScanSearch } from "lucide-react";
import { useI18n } from "../../shared/i18n";
import type { View, WorkspaceSettings, WorkspaceOverview as WorkspaceOverviewData } from "../../shared/types";

interface WorkspaceOverviewProps {
  overview: WorkspaceOverviewData;
  onRefresh: () => void;
  refreshing: boolean;
  settings: WorkspaceSettings | null;
  onNavigate: (view: View) => void;
  onOpenWorkflow: (flowId: string) => void;
}

export function WorkspaceOverview({
  overview,
  onRefresh,
  refreshing,
  settings,
  onNavigate,
  onOpenWorkflow,
}: WorkspaceOverviewProps): React.JSX.Element {
  const { formatDate, t } = useI18n();

  return (
    <div className="page-stack workspace-home">
      <div className="page-heading">
        <div>
          <h1>{overview.name}</h1>
          <p className="muted path-line"><HardDrive size={15} />{overview.path}</p>
        </div>
        <button className="button button-secondary" type="button" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "spin" : ""} />{t("overview.refresh")}
        </button>
      </div>

      <div className="workspace-summary" aria-label={t("overview.eyebrow")}>
        <span><FolderGit2 size={15} /><strong>{overview.repositories.length}</strong> {t("overview.repositories")}</span>
        <span><CheckCircle2 size={15} /><strong>{t("overview.initialized")}</strong></span>
        <span><GitBranch size={15} />{t("overview.id")} <code>{overview.workspace_id.slice(0, 8)}</code></span>
      </div>

      <section className="workspace-shortcuts" aria-labelledby="workspace-tools-title">
        <h2 id="workspace-tools-title">{t("overview.tools")}</h2>
        <div className="workspace-shortcut-grid">
          <button type="button" onClick={() => onNavigate("agent")}><span className="workspace-glyph glyph-violet"><Bot size={21} /></span><span><strong>{t("app.agentSettings")}</strong><small>{t("overview.agentHint")}</small></span><ArrowUpRight size={14} /></button>
          <button type="button" onClick={() => onNavigate("flows")}><span className="workspace-glyph glyph-rose"><GitBranch size={21} /></span><span><strong>{t("app.flows")}</strong><small>{t("overview.flowsHint")}</small></span><ArrowUpRight size={14} /></button>
          <button type="button" onClick={() => onNavigate("capabilities")}><span className="workspace-glyph glyph-blue"><Puzzle size={21} /></span><span><strong>{t("app.capabilities")}</strong><small>{t("overview.capabilitiesHint")}</small></span><ArrowUpRight size={14} /></button>
          <button type="button" onClick={() => onNavigate("auto-scan")}><span className="workspace-glyph glyph-amber"><ScanSearch size={21} /></span><span><strong>{t("app.autoScan")}</strong><small>{t("overview.scanHint")}</small></span><ArrowUpRight size={14} /></button>
        </div>
      </section>

      <div className="workspace-columns">
      <section className="panel workspace-repositories">
        <div className="panel-heading">
          <div>
            <h2>{t("overview.repositoriesTitle")}</h2>
          </div>
          <span className="panel-count">{overview.repositories.length}</span>
        </div>
        {overview.repositories.length === 0 ? (
          <div className="empty-inline">
            <FolderGit2 size={22} />
            <div><strong>{t("overview.emptyTitle")}</strong><p>{t("overview.emptyCopy")}</p></div>
          </div>
        ) : (
          <div className="repository-list">
            {overview.repositories.map((repository) => (
              <div className="repository-row" key={repository.name}>
                <div className="repository-main">
                  <span className="repository-mark"><FolderGit2 size={17} /></span>
                  <div><strong>{repository.name}</strong><code title={repository.path}>{repository.path}</code></div>
                </div>
                <div className="repository-meta">
                  <span><GitBranch size={14} />{repository.branch}</span>
                  <span className={repository.health === "ready" ? "health-ok" : "health-bad"}>
                    {repository.health === "ready" ? t("overview.healthNormal") : t("overview.healthAbnormal")}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
      <aside className="workspace-context">
        <section className="panel workspace-automation">
          <div className="panel-heading"><h2>{t("app.automationGroup")}</h2><Clock3 size={17} /></div>
          <p className="workspace-section-copy">{t("overview.automationHint")}</p>
          {settings && [
            { view: "auto-delivery" as const, label: t("app.autoDelivery"), config: settings.auto_delivery, Icon: Rocket },
            { view: "auto-scan" as const, label: t("app.autoScan"), config: settings.auto_scan, Icon: ScanSearch },
          ].map(({ view, label, config, Icon }) => (
            <button className="automation-summary" type="button" key={view} onClick={() => onNavigate(view)}>
              <Icon size={18} /><span><strong>{label}</strong><small className={config.enabled ? "health-ok" : "muted"}>{config.enabled ? t("settings.enabled") : t("settings.disabled")}</small><code>{config.schedule_expression || t("overview.unscheduled")}</code></span><ArrowUpRight size={14} />
            </button>
          ))}
          {overview.workflow_schedules.map((workflow) => (
            <button className="automation-summary" type="button" key={workflow.flow_id} onClick={() => onOpenWorkflow(workflow.flow_id)}>
              <GitBranch size={18} /><span><strong>{workflow.name}</strong><small className={workflow.enabled ? "health-ok" : "muted"}>{workflow.enabled ? t("settings.enabled") : t("settings.disabled")}</small><code>{workflow.schedule_expression}</code></span><ArrowUpRight size={14} />
            </button>
          ))}
        </section>
        <section className="workspace-details">
          <h2>{t("overview.details")}</h2>
          <dl><div><dt>{t("overview.id")}</dt><dd className="mono">{overview.workspace_id}</dd></div><div><dt>{t("overview.created")}</dt><dd>{formatDate(overview.created_at)}</dd></div><div><dt>{t("overview.initialVersion")}</dt><dd>{overview.lumon_version}</dd></div></dl>
        </section>
      </aside>
      </div>
    </div>
  );
}
