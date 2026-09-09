import { CheckCircle2, FolderGit2, GitBranch, HardDrive, RefreshCw } from "lucide-react";
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
  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace overview</p>
          <h1>{overview.name}</h1>
          <p className="muted path-line"><HardDrive size={15} />{overview.path}</p>
        </div>
        <button className="button button-secondary" type="button" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "spin" : ""} />刷新
        </button>
      </div>

      <div className="metric-grid">
        <article className="metric-card">
          <span className="metric-icon accent-blue"><FolderGit2 size={18} /></span>
          <span className="metric-label">Repositories</span>
          <strong>{overview.repositories.length}</strong>
          <small>已登记代码仓库</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon accent-green"><CheckCircle2 size={18} /></span>
          <span className="metric-label">Workspace 状态</span>
          <strong>已初始化</strong>
          <small>Lumon {overview.lumon_version}</small>
        </article>
        <article className="metric-card">
          <span className="metric-icon accent-purple"><GitBranch size={18} /></span>
          <span className="metric-label">Workspace ID</span>
          <strong className="mono metric-id">{overview.workspace_id.slice(0, 8)}</strong>
          <small>创建于 {formatDate(overview.created_at)}</small>
        </article>
      </div>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Repository mapping</p>
            <h2>代码仓库</h2>
          </div>
          <span className="panel-count">{overview.repositories.length}</span>
        </div>
        {overview.repositories.length === 0 ? (
          <div className="empty-inline">
            <FolderGit2 size={22} />
            <div><strong>还没有 Repository</strong><p>可以通过 CLI 的 init 流程添加代码仓库。</p></div>
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
                    {repository.health === "ready" ? "正常" : "异常"}
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

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString("zh-CN");
}
