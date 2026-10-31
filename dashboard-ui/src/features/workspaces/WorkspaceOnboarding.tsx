import { FolderOpen, FolderPlus, LoaderCircle, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { dashboardApi } from "../../app/api";
import { LanguagePicker, useI18n } from "../../shared/i18n";
import type { RemoteRepository, SetupReport, WorkspaceListItem } from "../../shared/types";
import { SetupChecklist } from "./SetupChecklist";
import { useRepositoryCatalog } from "./useRepositoryCatalog";
import "./RepositoriesPage.css";
import "./WorkspaceOnboarding.css";

interface WorkspaceOnboardingProps {
  onReady: (workspace: WorkspaceListItem, view?: "overview" | "settings") => void;
  onError: (message: string) => void;
  onCancel?: () => void;
}

type BranchPage = { names: string[]; page: number; more: boolean };

export function WorkspaceOnboarding({ onReady, onError, onCancel }: WorkspaceOnboardingProps): React.JSX.Element {
  const { t } = useI18n();
  const [mode, setMode] = useState<"initialize" | "register">("initialize");
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [repositories, setRepositories] = useState("");
  const [setup, setSetup] = useState<SetupReport | null>(null);
  const [checking, setChecking] = useState(true);
  const [setupError, setSetupError] = useState("");
  const [host, setHost] = useState("");
  const [organization, setOrganization] = useState("");
  const [organizations, setOrganizations] = useState<string[]>([]);
  const [organizationPage, setOrganizationPage] = useState(1);
  const [moreOrganizations, setMoreOrganizations] = useState(false);
  const [loadingOrganizations, setLoadingOrganizations] = useState(false);
  const [selected, setSelected] = useState<Record<string, RemoteRepository>>({});
  const [branches, setBranches] = useState<Record<string, BranchPage>>({});
  const [branchLoading, setBranchLoading] = useState<Record<string, boolean>>({});
  const [pickerError, setPickerError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pickingFolder, setPickingFolder] = useState(false);
  const [created, setCreated] = useState<WorkspaceListItem | null>(null);
  const mounted = useRef(true);
  const setupRequest = useRef(0);
  const organizationRequest = useRef(0);
  const branchRequests = useRef(new Set<string>());
  const submitPending = useRef(false);
  const catalog = useRepositoryCatalog(mode === "initialize" && !created ? host : "", organization);

  useEffect(() => {
    mounted.current = true;
    void checkSetup();
    return () => { mounted.current = false; setupRequest.current += 1; organizationRequest.current += 1; };
  }, []);

  async function checkSetup(): Promise<void> {
    const request = ++setupRequest.current;
    setChecking(true);
    setSetupError("");
    try {
      const report = await dashboardApi.getSetup();
      if (!mounted.current || request !== setupRequest.current) return;
      setSetup(report);
      setHost((current) => report.hosts.includes(current) ? current : report.hosts[0] ?? "");
    } catch (error) {
      if (mounted.current && request === setupRequest.current) setSetupError(error instanceof Error ? error.message : t("setup.failed"));
    } finally {
      if (mounted.current && request === setupRequest.current) setChecking(false);
    }
  }

  useEffect(() => {
    setOrganization(""); setOrganizations([]); setMoreOrganizations(false); setOrganizationPage(1);
    if (host) void loadOrganizations(host);
    return () => { organizationRequest.current += 1; };
  }, [host]);

  async function loadOrganizations(source: string, page = 1): Promise<void> {
    setPickerError("");
    const request = ++organizationRequest.current;
    setLoadingOrganizations(true);
    try {
      const items = await dashboardApi.repositoryOrganizations(source, page);
      if (!mounted.current || request !== organizationRequest.current) return;
      setOrganizations((previous) => page === 1 ? items : [...new Set([...previous, ...items])]);
      setOrganizationPage(page); setMoreOrganizations(items.length === 100);
    } catch (error) {
      if (mounted.current && request === organizationRequest.current) setPickerError(error instanceof Error ? error.message : t("onboarding.operationFailed"));
    } finally {
      if (mounted.current && request === organizationRequest.current) setLoadingOrganizations(false);
    }
  }

  async function refreshEnvironment(): Promise<void> {
    await checkSetup();
    if (host && !created) {
      void loadOrganizations(host);
      void catalog.search(catalog.query.trim());
    }
  }

  function toggleRepository(item: RemoteRepository): void {
    setSelected((previous) => {
      const updated = { ...previous };
      if (updated[item.clone_url]) delete updated[item.clone_url];
      else updated[item.clone_url] = item;
      return updated;
    });
  }

  function configure(item: RemoteRepository, patch: Partial<RemoteRepository>): void {
    setSelected((previous) => previous[item.clone_url] ? { ...previous, [item.clone_url]: { ...previous[item.clone_url], ...patch } } : previous);
  }

  async function loadBranches(item: RemoteRepository, more = false): Promise<void> {
    const key = item.clone_url;
    if (branchRequests.current.has(key) || (!more && branches[key])) return;
    branchRequests.current.add(key); setBranchLoading((previous) => ({ ...previous, [key]: true })); setPickerError("");
    const page = more ? (branches[key]?.page ?? 0) + 1 : 1;
    try {
      const names = await dashboardApi.sourceRepositoryBranches(new URL(key).hostname, item.full_name, page);
      if (mounted.current) setBranches((previous) => ({ ...previous, [key]: { names: [...new Set([...(page === 1 ? [] : previous[key]?.names ?? []), ...names])], page, more: names.length === 100 } }));
    } catch (error) {
      if (mounted.current) setPickerError(error instanceof Error ? error.message : t("onboarding.operationFailed"));
    } finally {
      branchRequests.current.delete(key);
      if (mounted.current) setBranchLoading((previous) => ({ ...previous, [key]: false }));
    }
  }

  async function chooseFolder(): Promise<void> {
    setPickingFolder(true);
    try {
      const selection = await dashboardApi.selectWorkspaceFolder();
      if (selection.path) setPath(selection.path);
    } catch (error) { onError(error instanceof Error ? error.message : t("onboarding.folderSelectionFailed")); }
    finally { setPickingFolder(false); }
  }

  async function submit(): Promise<void> {
    if (submitPending.current) return;
    if (!path.trim()) { onError(t("onboarding.pathRequired")); return; }
    if (mode === "initialize" && !Object.keys(selected).length && !repositories.trim()) { onError(t("onboarding.repoRequired")); return; }
    submitPending.current = true; setSubmitting(true);
    try {
      if (mode === "register") setCreated(await dashboardApi.registerWorkspace(path.trim()));
      else {
        const response = await dashboardApi.initializeWorkspace({
          path: path.trim(), ...(name.trim() ? { name: name.trim() } : {}),
          repositories: repositories.split("\n").map((value) => value.trim()).filter(Boolean),
          remote_repositories: Object.values(selected),
        });
        const workspace = (await dashboardApi.listWorkspaces()).find((item) => item.workspace_id === response.workspace_id);
        if (!workspace) throw new Error(t("onboarding.reloadFailed"));
        setCreated(workspace);
      }
      void checkSetup();
    } catch (error) { onError(error instanceof Error ? error.message : t("onboarding.operationFailed")); }
    finally { submitPending.current = false; setSubmitting(false); }
  }

  const rows = [...catalog.results, ...Object.values(selected).filter((item) => !catalog.results.some((result) => result.clone_url === item.clone_url))];
  const ready = setup?.ready && setup.agent_configured;
  const title = onCancel ? t("picker.addWorkspace") : t("onboarding.title");

  return <main className="onboarding-wrap"><section className={`onboarding-card onboarding-v2 ${created ? "onboarding-complete" : ""}`}>
    <LanguagePicker className="onboarding-language" />
    <div className="onboarding-brand"><img className="onboarding-logo" src="/lumon-mark.png" alt={t("app.brandAlt")} /><strong>Lumon</strong></div>
    <div className="onboarding-heading"><h1>{created ? t("onboarding.created") : title}</h1>
      {onCancel && !created && <button type="button" className="button button-secondary" disabled={submitting} onClick={onCancel}>{t("onboarding.cancel")}</button>}
    </div>
    {created ? <><p className="onboarding-created-name">{created.name}</p><SetupChecklist report={setup} loading={checking} error={setupError} onRefresh={() => void refreshEnvironment()} />
      <p className="setup-agent-state">{setup?.agent_configured ? t("setup.agentConfigured") : t("setup.agentPending")}</p>
      <button type="button" className="button button-primary button-wide" disabled={checking} onClick={() => onReady(created, ready ? "overview" : "settings")}>{ready ? t("onboarding.openOverview") : t("onboarding.openSettings")}</button>
    </> : <>
      <SetupChecklist report={setup} loading={checking} error={setupError} onRefresh={() => void refreshEnvironment()} />
      <div className="segmented-control" role="tablist" aria-label={t("onboarding.operationAria")}>
        <button type="button" role="tab" aria-selected={mode === "initialize"} className={mode === "initialize" ? "active" : ""} disabled={submitting} onClick={() => setMode("initialize")}><FolderPlus size={16} />{t("onboarding.initializeNew")}</button>
        <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} disabled={submitting} onClick={() => setMode("register")}><Plus size={16} />{t("onboarding.addExisting")}</button>
      </div>
      <fieldset className="onboarding-form" disabled={submitting}><legend className="sr-only">{title}</legend>
        <div className="onboarding-workspace-fields"><div><label className="field-label" htmlFor="workspace-path">{t("onboarding.workspacePath")}</label><div className="path-picker"><input id="workspace-path" className="text-input" value={path} onChange={(event) => setPath(event.target.value)} placeholder={t("onboarding.workspacePathPlaceholder")} /><button className="button button-secondary" type="button" disabled={pickingFolder} onClick={() => void chooseFolder()} aria-label={t("onboarding.chooseFolderAria")}>{pickingFolder ? <LoaderCircle size={16} className="spin" /> : <FolderOpen size={16} />}{t("onboarding.chooseFolder")}</button></div></div>
          {mode === "initialize" && <div><label className="field-label" htmlFor="workspace-name">{t("onboarding.nameOptional")}</label><input id="workspace-name" className="text-input" value={name} onChange={(event) => setName(event.target.value)} placeholder={t("onboarding.namePlaceholder")} /></div>}
        </div>
        {mode === "initialize" && <>
          {host && <section className="onboarding-repositories" aria-label={t("app.repositories")}>
            <div className="onboarding-source-fields"><div><label className="field-label" htmlFor="repository-source">{t("onboarding.source")}</label><select id="repository-source" className="text-input" value={host} onChange={(event) => setHost(event.target.value)}>{setup?.hosts.map((item) => <option value={item} key={item}>{item}</option>)}</select></div>
              <div><label className="field-label" htmlFor="repository-organization">{t("onboarding.organization")}</label><select id="repository-organization" className="text-input" value={organization} disabled={loadingOrganizations} onChange={(event) => { if (event.target.value === "__more__") void loadOrganizations(host, organizationPage + 1); else setOrganization(event.target.value); }}><option value="">{t("onboarding.allRepositories")}</option>{organizations.map((item) => <option key={item} value={item}>{item}</option>)}{moreOrganizations && <option value="__more__">{t("repository.loadMore")}</option>}</select></div>
            </div>
            <div className="onboarding-repository-search"><label className="sr-only" htmlFor="repository-search">{t("onboarding.repoSearch")}</label><input id="repository-search" className="text-input" value={catalog.query} onChange={(event) => catalog.setQuery(event.target.value)} placeholder={t("onboarding.filterOptional")} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void catalog.search(catalog.query.trim()); } }} /><button type="button" className="button button-secondary" disabled={catalog.loading} onClick={() => void catalog.search(catalog.query.trim())}>{t("onboarding.repoSearchAction")}</button><span className="onboarding-selected-count">{t("onboarding.repoSelected")} · {Object.keys(selected).length}</span></div>
            {(catalog.error || pickerError) && <p role="alert" className="repository-error">{catalog.error || pickerError}</p>}
            <div className="onboarding-repository-scroll table-scroll" tabIndex={0} aria-busy={catalog.loading}><table className="repository-table onboarding-repository-table"><thead><tr><th scope="col"><span className="sr-only">{t("onboarding.selectRepository")}</span></th><th scope="col">{t("repository.name")}</th><th scope="col">{t("onboarding.repoBranch")}</th><th scope="col">Auto Scan</th><th scope="col">Auto Delivery</th></tr></thead><tbody>{rows.map((original) => {
              const item = selected[original.clone_url] ?? original; const isSelected = !!selected[item.clone_url];
              return <tr key={item.clone_url} className={isSelected ? "is-selected" : ""}><td><input className="repository-choice" type="checkbox" aria-label={item.full_name} checked={isSelected} onChange={() => toggleRepository(item)} /></td><td><strong title={item.full_name}>{item.full_name}</strong></td><td><select className="text-input repository-branch-input" aria-label={`${item.full_name} ${t("onboarding.repoBranch")}`} disabled={!isSelected} aria-busy={branchLoading[item.clone_url] ?? false} value={item.branch} onFocus={() => void loadBranches(item)} onPointerDown={() => void loadBranches(item)} onChange={(event) => { if (event.target.value === "__more__") void loadBranches(item, true); else configure(item, { branch: event.target.value }); }}>
                {[...new Set([item.branch, ...branches[item.clone_url]?.names ?? []])].map((branch) => <option value={branch} key={branch}>{branch}</option>)}{branches[item.clone_url]?.more && <option value="__more__">{t("repository.loadMore")}</option>}</select></td>{(["auto_scan", "auto_delivery"] as const).map((field) => <td className="repository-toggle-cell" key={field}><label className="settings-toggle"><input type="checkbox" role="switch" aria-label={`${item.full_name} ${field === "auto_scan" ? "Auto Scan" : "Auto Delivery"}`} disabled={!isSelected} checked={isSelected && item[field]} onChange={(event) => configure(item, { [field]: event.target.checked })} /><span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span></label></td>)}</tr>;
            })}</tbody></table>{!rows.length && <p className="repository-empty" role="status">{catalog.loading ? t("app.loading") : t("onboarding.repoEmpty")}</p>}</div>
            {catalog.hasMore && <div className="repository-pagination"><button className="button button-secondary" type="button" disabled={catalog.loading} onClick={() => void catalog.loadMore()}>{t("repository.loadMore")}</button></div>}
          </section>}
          <details className="repository-picker-manual"><summary>{t("onboarding.manual")}</summary><label className="field-label" htmlFor="workspace-repositories">{t("onboarding.repositoryUrlOptional")}</label><textarea id="workspace-repositories" className="text-input text-area" value={repositories} onChange={(event) => setRepositories(event.target.value)} placeholder={t("onboarding.repositoryPlaceholder")} rows={3} /></details>
        </>}
      </fieldset>
      <button className="button button-primary button-wide" type="button" onClick={() => void submit()} disabled={submitting || checking}>{submitting ? <LoaderCircle size={17} className="spin" /> : <FolderPlus size={17} />}{submitting ? t("onboarding.processing") : mode === "initialize" ? t("onboarding.initializeAction") : t("onboarding.addAction")}</button>
    </>}
  </section></main>;
}
