import { CheckCircle2, FolderGit2, GitBranch, HardDrive, RefreshCw } from "lucide-react";
import { useI18n } from "../../shared/i18n";
import type { WorkspaceOverview as WorkspaceOverviewData } from "../../shared/types";

interface WorkspaceOverviewProps {
  overview: WorkspaceOverviewData;
  onRefresh: () => void;
  refreshing: boolean;
}

export function WorkspaceOverview({
  overview,
  onRefresh,
  refreshing,
}: WorkspaceOverviewProps): React.JSX.Element {
  const { formatDate, t } = useI18n();

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">{t("overview.eyebrow")}</p>
          <h1>{overview.name}</h1>
          <p className="muted path-line"><HardDrive size={15} />{overview.path}</p>
        </div>
        <button className="button button-secondary" type="button" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "spin" : ""} />{t("overview.refresh")}
        </button>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <span className="metric-icon accent-blue"><FolderGit2 size={18} /></span>
          <span className="metric-label">{t("overview.repositories")}</span>
          <strong>{overview.repositories.length}</strong>
          <small>{t("overview.registeredRepositories")}</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon accent-green"><CheckCircle2 size={18} /></span>
          <span className="metric-label">{t("overview.status")}</span>
          <strong>{t("overview.initialized")}</strong>
          <small>{t("overview.version", { version: overview.lumon_version })}</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon accent-purple"><GitBranch size={18} /></span>
          <span className="metric-label">{t("overview.id")}</span>
          <strong className="mono metric-id">{overview.workspace_id.slice(0, 8)}</strong>
          <small>{t("overview.createdAt", { date: formatDate(overview.created_at) })}</small>
        </article>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">{t("overview.mappingEyebrow")}</p>
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
                  <div><strong>{repository.name}</strong><code>{repository.path}</code></div>
                </div>
                <div className="repository-meta">
                  <span><GitBranch size={14} />{repository.branch}</span>
                  <span className={repository.health === "ready" ? "health-ok" : "health-bad"}>
                    {repository.health === "ready" ? t("overview.healthNormal") : t("overview.healthAbnormal")}
                  </span>
                  <code title={repository.revision}>{repository.revision.slice(0, 12)}</code>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
