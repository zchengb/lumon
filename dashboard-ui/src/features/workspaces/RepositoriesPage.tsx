import { Check, GitBranch, LoaderCircle, Plus, RefreshCw, Search } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { RemoteRepository, WorkspaceOverview } from "../../shared/types";
import "./RepositoriesPage.css";
import { useRepositoryCatalog } from "./useRepositoryCatalog";

type Scope = { name: string; auto_scan: boolean; auto_delivery: boolean };

interface RepositoriesPageProps {
  overview: WorkspaceOverview;
  onRefresh: () => Promise<void>;
  onDirtyChange: (dirty: boolean) => void;
  onNotice: (message: string) => void;
}

export function RepositoriesPage({ overview, onRefresh, onDirtyChange, onNotice }: RepositoriesPageProps): React.JSX.Element {
  const { t } = useI18n();
  const [tab, setTab] = useState<"workspace" | "github">(overview.repositories.length ? "workspace" : "github");
  const [scopes, setScopes] = useState<Scope[]>(() => overview.repositories.map((item) => ({
    name: item.name, auto_scan: item.auto_scan ?? true, auto_delivery: item.auto_delivery ?? true,
  })));
  const [scopeVersion, setScopeVersion] = useState(overview.repositories_version);
  const [targetBranches, setTargetBranches] = useState<Record<string, string>>(() => Object.fromEntries(overview.repositories.map((item) => [item.name, item.branch])));
  const [branchOptions, setBranchOptions] = useState<Record<string, string[]>>({});
  const [loadingBranches, setLoadingBranches] = useState<Record<string, boolean>>({});
  const branchRequests = useRef(new Set<string>());
  const [hosts, setHosts] = useState<string[]>([]);
  const [host, setHost] = useState("");
  const [loadingSources, setLoadingSources] = useState(true);
  const [saving, setSaving] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState("");
  const mutationPending = useRef(false);
  const busy = saving || connecting !== null;
  const [sourceError, setSourceError] = useState("");
  const { results, setResults, query, setQuery, loading, hasMore, search, loadMore, error: searchError } = useRepositoryCatalog(host, "");
  const catalogError = sourceError || searchError;

  useEffect(() => {
    setScopeVersion(overview.repositories_version);
    setTargetBranches(Object.fromEntries(overview.repositories.map((item) => [item.name, item.branch])));
    setScopes(overview.repositories.map((item) => ({
      name: item.name, auto_scan: item.auto_scan ?? true, auto_delivery: item.auto_delivery ?? true,
    })));
  }, [overview.workspace_id, overview.repositories_version]);

  useEffect(() => {
    let cancelled = false;
    void dashboardApi.repositorySources().then((items) => {
      if (cancelled) return;
      setHosts(items);
      setHost((current) => items.includes(current) ? current : items[0] || "");
    }).catch((reason: unknown) => {
      if (!cancelled) setSourceError(reason instanceof Error ? reason.message : t("onboarding.operationFailed"));
    }).finally(() => { if (!cancelled) setLoadingSources(false); });
    return () => { cancelled = true; };
  }, [t]);

  useEffect(() => { onDirtyChange(saving); }, [saving, onDirtyChange]);

  function navigateTabs(event: KeyboardEvent<HTMLDivElement>): void {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let next: "workspace" | "github" = tab === "workspace" ? "github" : "workspace";
    if (event.key === "Home") next = "workspace";
    if (event.key === "End") next = "github";
    setTab(next);
    event.currentTarget.querySelector<HTMLButtonElement>(`#${next}-repositories-tab`)?.focus();
  }

  async function setScope(name: string, field: "auto_scan" | "auto_delivery", checked: boolean): Promise<void> {
    if (!scopeVersion || mutationPending.current) return;
    const previous = scopes;
    const updated = scopes.map((item) => item.name === name ? { ...item, [field]: checked } : item);
    setScopes(updated);
    await saveRepositoryChange(
      () => dashboardApi.updateRepositoryScopes(overview.workspace_id, scopeVersion, updated),
      () => setScopes(previous),
    );
  }

  async function loadBranches(name: string): Promise<void> {
    if (branchRequests.current.has(name) || branchOptions[name]) return;
    branchRequests.current.add(name);
    setLoadingBranches((current) => ({ ...current, [name]: true }));
    setError("");
    try {
      const names = await dashboardApi.repositoryBranches(overview.workspace_id, name);
      setBranchOptions((current) => ({ ...current, [name]: names }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("onboarding.operationFailed"));
    } finally {
      branchRequests.current.delete(name);
      setLoadingBranches((current) => ({ ...current, [name]: false }));
    }
  }

  async function setBranch(name: string, branch: string): Promise<void> {
    if (!scopeVersion || mutationPending.current || targetBranches[name] === branch) return;
    const previous = targetBranches[name];
    setTargetBranches((current) => ({ ...current, [name]: branch }));
    await saveRepositoryChange(
      () => dashboardApi.updateRepositoryBranch(overview.workspace_id, name, scopeVersion, branch),
      () => {
        setTargetBranches((current) => ({ ...current, [name]: previous }));
        setBranchOptions((current) => { const updated = { ...current }; delete updated[name]; return updated; });
      },
    );
  }

  async function saveRepositoryChange(save: () => Promise<{ repositories_version: string }>, rollback: () => void): Promise<void> {
    mutationPending.current = true;
    setSaving(true);
    setError("");
    let saved = false;
    try {
      const response = await save();
      saved = true;
      setScopeVersion(response.repositories_version);
      await onRefresh();
      onNotice(t("app.settingsSaved"));
    } catch (reason) {
      if (!saved) rollback();
      setError(reason instanceof Error ? reason.message : t("onboarding.operationFailed"));
    } finally {
      mutationPending.current = false;
      setSaving(false);
    }
  }

  async function connect(item: RemoteRepository): Promise<void> {
    if (!scopeVersion || mutationPending.current) return;
    mutationPending.current = true;
    setConnecting(item.clone_url);
    setError("");
    const existing = overview.repositories.find((repository) => repository.name === item.name);
    const scope = scopes.find((repository) => repository.name === item.name);
    try {
      await dashboardApi.addRepositories(overview.workspace_id, scopeVersion, [{
        ...item, branch: targetBranches[item.name] ?? existing?.branch ?? item.branch,
        auto_scan: scope?.auto_scan ?? existing?.auto_scan ?? true,
        auto_delivery: scope?.auto_delivery ?? existing?.auto_delivery ?? true,
      }]);
      await onRefresh();
      onNotice(t("app.settingsSaved"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("onboarding.operationFailed"));
    } finally {
      mutationPending.current = false;
      setConnecting(null);
    }
  }

  return <div className="page-stack repositories-page">
    <div className="page-heading">
      <h1>{t("app.repositories")}</h1>
    </div>
    <section className="panel repository-panel">
      <div className="panel-heading">
        <div className="segmented-control" role="tablist" aria-label={t("app.repositories")} onKeyDown={navigateTabs}>
          <button id="workspace-repositories-tab" role="tab" tabIndex={tab === "workspace" ? 0 : -1} aria-selected={tab === "workspace"} aria-controls="workspace-repositories" className={tab === "workspace" ? "active" : ""} type="button" onClick={() => setTab("workspace")}>{t("app.currentWorkspace")} <span className="repository-tab-count">{overview.repositories.length}</span></button>
          <button id="github-repositories-tab" role="tab" tabIndex={tab === "github" ? 0 : -1} aria-selected={tab === "github"} aria-controls="github-repositories" className={tab === "github" ? "active" : ""} type="button" onClick={() => setTab("github")}>GitHub MCP</button>
        </div>
        {tab === "github" && hosts.length > 0 && <select className="text-input repository-source" aria-label={t("onboarding.source")} value={host} disabled={busy} onChange={(event) => setHost(event.target.value)}>{hosts.map((item) => <option key={item} value={item}>{item}</option>)}</select>}
      </div>
      {error && <p className="repository-error" role="alert">{error}</p>}
      {tab === "workspace" && <div id="workspace-repositories" role="tabpanel" aria-labelledby="workspace-repositories-tab" aria-busy={saving}>
        {overview.repositories.length === 0 ? <p className="repository-empty">{t("overview.emptyTitle")}</p> : <div className="table-scroll" tabIndex={0}><table className="repository-table">
          <thead><tr><th scope="col">{t("repository.name")}</th><th scope="col">{t("onboarding.repoBranch")}</th><th scope="col" className="repository-toggle-cell">Auto Scan</th><th scope="col" className="repository-toggle-cell">Auto Delivery</th></tr></thead>
          <tbody>{overview.repositories.map((item) => {
            const scope = scopes.find((entry) => entry.name === item.name);
            const branch = targetBranches[item.name] ?? item.branch;
            const options = [...new Set([branch, ...(branchOptions[item.name] ?? [])])];
            return <tr key={item.name}>
              <td><strong title={item.remote_name ?? item.path}>{item.name}</strong></td>
              <td><select className="text-input repository-branch-input" aria-label={`${item.name} ${t("onboarding.repoBranch")}`} aria-busy={loadingBranches[item.name] ?? false} value={branch} disabled={busy || !scopeVersion} onFocus={() => void loadBranches(item.name)} onPointerDown={() => void loadBranches(item.name)} onChange={(event) => void setBranch(item.name, event.target.value)}>
                {options.map((name) => <option key={name} value={name}>{name}</option>)}
                {loadingBranches[item.name] && <option disabled>{t("app.loading")}</option>}
              </select></td>
              {(["auto_scan", "auto_delivery"] as const).map((field) => <td className="repository-toggle-cell" key={field}><label className="settings-toggle">
                <input type="checkbox" role="switch" aria-label={`${item.name} ${field === "auto_scan" ? "Auto Scan" : "Auto Delivery"}`} checked={scope?.[field] ?? item[field] ?? true} disabled={busy || !scopeVersion} onChange={(event) => void setScope(item.name, field, event.target.checked)} />
                <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
              </label></td>)}
            </tr>;
          })}</tbody>
        </table></div>}
      </div>}
      {tab === "github" && <div id="github-repositories" role="tabpanel" aria-labelledby="github-repositories-tab" aria-busy={loading || loadingSources}>
        {host && <form className="repository-search" onSubmit={(event) => { event.preventDefault(); void search(query.trim()); }}>
          <div className="repository-search-input"><Search size={16} aria-hidden="true" /><input className="text-input" aria-label={t("onboarding.repoSearch")} value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("onboarding.repoSearchPlaceholder")} /></div>
          <button className="button button-secondary" type="submit" disabled={loading}>{t("onboarding.repoSearchAction")}</button>
          <button className="button button-secondary repository-refresh" type="button" aria-label={t("overview.refresh")} title={t("overview.refresh")} disabled={loading} onClick={() => void search(query.trim())}><RefreshCw size={16} /></button>
        </form>}
        {catalogError && <p className="repository-error" role="alert">{catalogError}</p>}
        {loadingSources || (loading && !results.length) ? <div className="repository-empty" role="status"><LoaderCircle size={18} className="spin" />{t("app.loading")}</div>
          : !host ? <p className="repository-empty">{!catalogError && t("onboarding.noSource")}</p>
          : !results.length ? <p className="repository-empty">{!catalogError && t("onboarding.repoEmpty")}</p>
          : <div className="table-scroll" tabIndex={0}><table className="repository-table repository-catalog">
            <thead><tr><th scope="col">{t("repository.name")}</th><th scope="col">{t("onboarding.repoBranch")}</th><th scope="col"><span className="sr-only">{t("repository.connect")}</span></th></tr></thead>
            <tbody>{results.map((item) => {
              const existing = overview.repositories.find((repository) => repository.name === item.name);
              const connected = existing?.mcp_server === item.mcp_server && existing?.remote_name === item.full_name;
              return <tr key={item.clone_url}>
                <td><strong>{item.full_name}</strong></td>
                <td>{existing ? <code className="repository-branch"><GitBranch size={13} />{targetBranches[existing.name] ?? existing.branch}</code> : <input className="text-input repository-branch-input" value={item.branch} aria-label={`${item.full_name} ${t("onboarding.repoBranch")}`} disabled={busy} onChange={(event) => setResults((current) => current.map((entry) => entry.clone_url === item.clone_url ? { ...entry, branch: event.target.value } : entry))} />}</td>
                <td className="repository-connect-cell">{connected ? <span className="repository-connected"><Check size={14} />{t("repository.connected")}</span> : <button className="button button-secondary" type="button" aria-label={`${t("repository.connect")} ${item.full_name}`} disabled={busy || !item.branch.trim() || !scopeVersion} onClick={() => void connect(item)}>{connecting === item.clone_url ? <LoaderCircle size={14} className="spin" /> : <Plus size={14} />}{t("repository.connect")}</button>}</td>
              </tr>;
            })}</tbody>
          </table></div>}
        {hasMore && <div className="repository-pagination"><button className="button button-secondary" type="button" disabled={loading || busy} onClick={() => void loadMore()}>{loading && <LoaderCircle size={15} className="spin" />}{t("repository.loadMore")}</button></div>}
      </div>}
    </section>
  </div>;
}
