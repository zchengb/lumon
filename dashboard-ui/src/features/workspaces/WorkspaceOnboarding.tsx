import { FolderOpen, FolderPlus, GitBranch, LoaderCircle, Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { LanguagePicker, useI18n } from "../../shared/i18n";
import type { RemoteRepository, WorkspaceListItem } from "../../shared/types";

interface WorkspaceOnboardingProps {
  onReady: (workspace: WorkspaceListItem) => void;
  onError: (message: string) => void;
}

type OnboardingMode = "initialize" | "register";

export function WorkspaceOnboarding({ onReady, onError }: WorkspaceOnboardingProps): React.JSX.Element {
  const { t } = useI18n();
  const [mode, setMode] = useState<OnboardingMode>("initialize");
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [repositories, setRepositories] = useState("");
  const [hosts, setHosts] = useState<string[]>([]);
  const [host, setHost] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RemoteRepository[]>([]);
  const [selected, setSelected] = useState<RemoteRepository[]>([]);
  const [searched, setSearched] = useState(false);
  const [searching, setSearching] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pickingFolder, setPickingFolder] = useState(false);

  useEffect(() => {
    void dashboardApi.repositorySources().then((sources) => {
      setHosts(sources);
      setHost((current) => current || sources[0] || "");
    }).catch((error: unknown) => setSourceError(error instanceof Error ? error.message : t("onboarding.operationFailed")));
  }, [t]);

  async function search(): Promise<void> {
    if (!host || !query.trim()) return;
    setSearching(true);
    try {
      setResults(await dashboardApi.searchRepositories(host, query.trim()));
      setSearched(true);
    } catch (error) {
      onError(error instanceof Error ? error.message : t("onboarding.operationFailed"));
    } finally {
      setSearching(false);
    }
  }

  function toggleRepository(repository: RemoteRepository): void {
    setSelected((current) => current.some((item) => item.clone_url === repository.clone_url)
      ? current.filter((item) => item.clone_url !== repository.clone_url)
      : [...current, repository]);
  }

  async function chooseFolder(): Promise<void> {
    setPickingFolder(true);
    try {
      const selection = await dashboardApi.selectWorkspaceFolder();
      if (selection.path) setPath(selection.path);
    } catch (error) {
      onError(error instanceof Error ? error.message : t("onboarding.folderSelectionFailed"));
    } finally {
      setPickingFolder(false);
    }
  }

  async function submit(): Promise<void> {
    const normalizedPath = path.trim();
    if (!normalizedPath) {
      onError(t("onboarding.pathRequired"));
      return;
    }
    if (mode === "initialize" && !selected.length && !repositories.trim()) {
      onError(t("onboarding.repoRequired"));
      return;
    }
    if (mode === "initialize" && selected.some((item) => !item.branch.trim())) {
      onError(t("onboarding.branchRequired"));
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "register") {
        onReady(await dashboardApi.registerWorkspace(normalizedPath));
      } else {
        const response = await dashboardApi.initializeWorkspace({
          path: normalizedPath,
          ...(name.trim() ? { name: name.trim() } : {}),
          repositories: repositories.split("\n").map((value) => value.trim()).filter(Boolean),
          remote_repositories: selected,
        });
        const workspaces = await dashboardApi.listWorkspaces();
        const created = workspaces.find((item) => item.workspace_id === response.workspace_id);
        if (!created) throw new Error(t("onboarding.reloadFailed"));
        onReady(created);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : t("onboarding.operationFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="onboarding-wrap">
      <section className="onboarding-card">
        <LanguagePicker className="onboarding-language" />
        <div className="onboarding-brand"><img className="onboarding-logo" src="/lumon-mark.png" alt={t("app.brandAlt")} /><div><strong>Lumon</strong><span>{t("app.workspaceConsole")}</span></div></div>
        <p className="eyebrow">{t("onboarding.localEyebrow")}</p>
        <h1>{t("onboarding.title")}</h1>
        <p className="onboarding-copy">{t("onboarding.copy")}</p>

        <div className="segmented-control" role="tablist" aria-label={t("onboarding.operationAria")}>
          <button className={mode === "initialize" ? "active" : ""} type="button" role="tab" aria-selected={mode === "initialize"} onClick={() => setMode("initialize")}>
            <FolderPlus size={16} />{t("onboarding.initializeNew")}
          </button>
          <button className={mode === "register" ? "active" : ""} type="button" role="tab" aria-selected={mode === "register"} onClick={() => setMode("register")}>
            <Plus size={16} />{t("onboarding.addExisting")}
          </button>
        </div>

        <label className="field-label" htmlFor="workspace-path">{t("onboarding.workspacePath")}</label>
        <div className="path-picker">
          <input id="workspace-path" className="text-input" value={path} onChange={(event) => setPath(event.target.value)} placeholder={t("onboarding.workspacePathPlaceholder")} />
          <button className="button button-secondary path-picker-button" type="button" onClick={() => void chooseFolder()} disabled={submitting || pickingFolder} aria-label={t("onboarding.chooseFolderAria")}>
            {pickingFolder ? <LoaderCircle size={16} className="spin" /> : <FolderOpen size={16} />}
            {pickingFolder ? t("onboarding.processing") : t("onboarding.chooseFolder")}
          </button>
        </div>

        {mode === "initialize" && (
          <>
            <label className="field-label" htmlFor="workspace-name">{t("onboarding.nameOptional")}</label>
            <input id="workspace-name" className="text-input" value={name} onChange={(event) => setName(event.target.value)} placeholder={t("onboarding.namePlaceholder")} />
            <label className="field-label" htmlFor="repository-source">{t("onboarding.source")}</label>
            {hosts.length ? (
              <>
                <select id="repository-source" className="text-input" value={host} onChange={(event) => { setHost(event.target.value); setResults([]); setSearched(false); }}>
                  {hosts.map((item) => <option value={item} key={item}>{item}</option>)}
                </select>
                <label className="field-label" htmlFor="repository-search">{t("onboarding.repoSearch")}</label>
                <div className="path-picker">
                  <input id="repository-search" className="text-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("onboarding.repoSearchPlaceholder")} onKeyDown={(event) => { if (event.key === "Enter") void search(); }} />
                  <button type="button" className="button button-secondary" disabled={searching || !query.trim()} onClick={() => void search()}>{searching ? <LoaderCircle size={16} className="spin" /> : t("onboarding.repoSearchAction")}</button>
                </div>
                {searched && !results.length && <p className="field-help">{t("onboarding.repoEmpty")}</p>}
                {results.length > 0 && <div className="repository-picker-results">{results.map((item) => (
                  <label key={item.clone_url} className="repository-picker-row">
                    <input type="checkbox" checked={selected.some((value) => value.clone_url === item.clone_url)} onChange={() => toggleRepository(item)} />
                    <span>{item.full_name}</span>
                  </label>
                ))}</div>}
              </>
            ) : <p className="field-help">{sourceError || t("onboarding.noSource")}</p>}
            {selected.length > 0 && <div className="repository-picker-selected">
              <strong>{t("onboarding.repoSelected")} · {selected.length}</strong>
              {selected.map((item) => <div className="repository-picker-branch" key={item.clone_url}>
                <span>{item.full_name}</span>
                <input className="text-input" aria-label={`${item.full_name} ${t("onboarding.repoBranch")}`} value={item.branch} onChange={(event) => setSelected((current) => current.map((value) => value.clone_url === item.clone_url ? { ...value, branch: event.target.value } : value))} />
                <button type="button" className="button button-secondary" onClick={() => toggleRepository(item)} aria-label={`${item.full_name} ×`}>×</button>
                <label><input type="checkbox" aria-label={`${item.full_name} Auto Scan`} checked={item.auto_scan} onChange={(event) => setSelected((current) => current.map((value) => value.clone_url === item.clone_url ? { ...value, auto_scan: event.target.checked } : value))} /> Auto Scan</label>
                <label><input type="checkbox" aria-label={`${item.full_name} Auto Delivery`} checked={item.auto_delivery} onChange={(event) => setSelected((current) => current.map((value) => value.clone_url === item.clone_url ? { ...value, auto_delivery: event.target.checked } : value))} /> Auto Delivery</label>
              </div>)}
            </div>}
            <details className="repository-picker-manual">
              <summary>{t("onboarding.manual")}</summary>
              <label className="field-label" htmlFor="workspace-repositories">{t("onboarding.repositoryUrlOptional")}</label>
              <textarea id="workspace-repositories" className="text-input text-area" value={repositories} onChange={(event) => setRepositories(event.target.value)} placeholder={t("onboarding.repositoryPlaceholder")} rows={3} />
              <p className="field-help"><GitBranch size={14} />{t("onboarding.authHelp")}</p>
            </details>
          </>
        )}

        <button className="button button-primary button-wide" type="button" onClick={() => void submit()} disabled={submitting}>
          {submitting ? <LoaderCircle size={17} className="spin" /> : mode === "initialize" ? <FolderPlus size={17} /> : <Plus size={17} />}
          {submitting ? t("onboarding.processing") : mode === "initialize" ? t("onboarding.initializeAction") : t("onboarding.addAction")}
        </button>
      </section>
    </main>
  );
}
