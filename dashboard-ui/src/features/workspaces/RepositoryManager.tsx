import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { RemoteRepository, WorkspaceOverview } from "../../shared/types";

type Scope = { name: string; auto_scan: boolean; auto_delivery: boolean };

export function RepositoryManager({ overview, onRefresh }: { overview: WorkspaceOverview; onRefresh: () => void }): React.JSX.Element {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [hosts, setHosts] = useState<string[]>([]);
  const [host, setHost] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RemoteRepository[]>([]);
  const [searched, setSearched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setScopes(overview.repositories.map((item) => ({
      name: item.name, auto_scan: item.auto_scan ?? true, auto_delivery: item.auto_delivery ?? true,
    })));
  }, [overview.workspace_id, overview.repositories_version]);

  useEffect(() => {
    if (!open) return;
    void dashboardApi.repositorySources().then((items) => { setHosts(items); setHost((value) => value || items[0] || ""); })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : t("onboarding.operationFailed")));
  }, [open, t]);

  async function run(action: () => Promise<void>): Promise<void> {
    setBusy(true);
    setError("");
    try { await action(); } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("onboarding.operationFailed"));
    } finally { setBusy(false); }
  }

  function setScope(name: string, field: "auto_scan" | "auto_delivery", checked: boolean): void {
    setScopes((current) => current.map((item) => item.name === name ? { ...item, [field]: checked } : item));
  }

  const changed = scopes.some((item) => {
    const original = overview.repositories.find((repository) => repository.name === item.name);
    return original && (item.auto_scan !== (original.auto_scan ?? true) || item.auto_delivery !== (original.auto_delivery ?? true));
  });

  return <details className="repository-manager" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>{t("repository.manage")}</summary>
    <h3>{t("repository.scope")}</h3>
    {scopes.map((item) => <div className="repository-manager-scope" key={item.name}>
      <strong>{item.name}</strong>
      <label><input type="checkbox" aria-label={`${item.name} Auto Scan`} checked={item.auto_scan} onChange={(event) => setScope(item.name, "auto_scan", event.target.checked)} /> Auto Scan</label>
      <label><input type="checkbox" aria-label={`${item.name} Auto Delivery`} checked={item.auto_delivery} onChange={(event) => setScope(item.name, "auto_delivery", event.target.checked)} /> Auto Delivery</label>
    </div>)}
    <button type="button" className="button button-secondary" disabled={busy || !changed || !overview.repositories_version} onClick={() => void run(async () => {
      await dashboardApi.updateRepositoryScopes(overview.workspace_id, overview.repositories_version!, scopes);
      onRefresh();
    })}>{t("repository.save")}</button>

    <h3>{t("repository.add")}</h3>
    {hosts.length ? <>
      <label className="field-label" htmlFor="manage-source">{t("onboarding.source")}</label>
      <select className="text-input" id="manage-source" value={host} onChange={(event) => { setHost(event.target.value); setResults([]); setSearched(false); }}>
        {hosts.map((item) => <option key={item} value={item}>{item}</option>)}
      </select>
      <label className="field-label" htmlFor="manage-query">{t("onboarding.repoSearch")}</label>
      <div className="path-picker">
        <input className="text-input" id="manage-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("onboarding.repoSearchPlaceholder")} />
        <button className="button button-secondary" type="button" disabled={busy || !query.trim()} onClick={() => void run(async () => {
          const found = await dashboardApi.searchRepositories(host, query.trim());
          setResults(found.map((item) => ({
            ...item, branch: overview.repositories.find((existing) => existing.name === item.name)?.branch ?? item.branch,
          })));
          setSearched(true);
        })}>{t("onboarding.repoSearchAction")}</button>
      </div>
      {searched && !results.length && <p className="field-help">{t("onboarding.repoEmpty")}</p>}
      {results.map((item) => {
        const existing = overview.repositories.find((repository) => repository.name === item.name);
        const connected = existing?.mcp_server === item.mcp_server && existing?.remote_name === item.full_name;
        return <div className="repository-manager-result" key={item.clone_url}>
          <span>{item.full_name}</span>
          <input className="text-input" value={item.branch} aria-label={`${item.full_name} ${t("onboarding.repoBranch")}`} onChange={(event) => setResults((values) => values.map((value) => value.clone_url === item.clone_url ? { ...value, branch: event.target.value } : value))} />
          <button className="button button-secondary" type="button" disabled={busy || changed || connected || !item.branch.trim() || !overview.repositories_version} onClick={() => void run(async () => {
            await dashboardApi.addRepositories(overview.workspace_id, overview.repositories_version!, [{ ...item, auto_scan: existing?.auto_scan ?? true, auto_delivery: existing?.auto_delivery ?? true }]);
            onRefresh();
          })}>{connected ? t("repository.connected") : t("repository.connect")}</button>
        </div>;
      })}
    </> : <p className="field-help">{t("onboarding.noSource")}</p>}
    {error && <p role="alert" className="health-bad">{error}</p>}
  </details>;
}
