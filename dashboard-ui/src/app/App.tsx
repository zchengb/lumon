import {
  AlertTriangle,
  CheckCircle2,
  LayoutDashboard,
  LoaderCircle,
  Settings,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ApiError, dashboardApi } from "./api";
import { readNavigation, writeNavigation } from "./navigation";
import { SettingsPage } from "../features/settings/SettingsPage";
import { WorkspaceOnboarding } from "../features/workspaces/WorkspaceOnboarding";
import { WorkspaceOverview } from "../features/workspaces/WorkspaceOverview";
import { WorkspacePicker } from "../features/workspaces/WorkspacePicker";
import { resolveWorkspaceSelection } from "../features/workspaces/workspaceSelection";
import { LanguagePicker, useI18n, type Translator } from "../shared/i18n";
import type { SettingsUpdate, View, WorkspaceListItem, WorkspaceOverview as WorkspaceOverviewData, WorkspaceSettings } from "../shared/types";

export function App(): React.JSX.Element {
  const { t } = useI18n();
  const initialNavigation = readNavigation(window.location.search);
  const [workspaces, setWorkspaces] = useState<WorkspaceListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialNavigation.workspaceId);
  const [view, setView] = useState<View>(initialNavigation.view);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const [overview, setOverview] = useState<WorkspaceOverviewData | null>(null);
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [settingsDirty, setSettingsDirty] = useState(false);

  const refreshWorkspaces = useCallback(async (): Promise<WorkspaceListItem[]> => {
    const next = await dashboardApi.listWorkspaces();
    setWorkspaces(next);
    setSelectedId((current) => resolveWorkspaceSelection(current, initialNavigation.workspaceId, next));
    return next;
  }, [initialNavigation.workspaceId]);

  useEffect(() => {
    void Promise.all([refreshWorkspaces(), dashboardApi.getBootstrap()])
      .then(([, bootstrap]) => setAppVersion(bootstrap.version))
      .catch((reason: unknown) => setError(messageFor(reason, t)))
      .finally(() => setLoading(false));
  }, [refreshWorkspaces, t]);

  useEffect(() => {
    if (!selectedId) {
      setOverview(null);
      setSettings(null);
      return;
    }
    let cancelled = false;
    setRefreshing(true);
    setError(null);
    Promise.all([dashboardApi.getOverview(selectedId), dashboardApi.getSettings(selectedId)])
      .then(([nextOverview, nextSettings]) => {
        if (cancelled) return;
        setOverview(nextOverview);
        setSettings(nextSettings);
      })
      .catch((reason: unknown) => { if (!cancelled) setError(messageFor(reason, t)); })
      .finally(() => { if (!cancelled) setRefreshing(false); });
    return () => { cancelled = true; };
  }, [selectedId, t]);

  useEffect(() => {
    window.history.replaceState(null, "", writeNavigation({ workspaceId: selectedId, view }));
  }, [selectedId, view]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 3500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  function changeWorkspace(nextId: string): void {
    if (settingsDirty && !window.confirm(t("app.unsavedWorkspaceConfirm"))) return;
    setSettingsDirty(false);
    setSelectedId(nextId);
  }

  function changeView(nextView: View): void {
    if (nextView === view) return;
    if (settingsDirty && !window.confirm(t("app.unsavedViewConfirm"))) return;
    setSettingsDirty(false);
    setView(nextView);
  }

  async function handleOnboardingReady(workspace: WorkspaceListItem): Promise<void> {
    try {
      setWorkspaces(await dashboardApi.listWorkspaces());
      setSelectedId(workspace.workspace_id);
      setView("overview");
      setNotice(t("app.workspaceReady", { name: workspace.name }));
      setError(null);
    } catch (reason) {
      setError(messageFor(reason, t));
    }
  }

  async function saveSettings(update: SettingsUpdate): Promise<boolean> {
    if (!selectedId) return false;
    try {
      const saved = await dashboardApi.updateSettings(selectedId, update);
      setSettings(saved);
      setNotice(t("app.settingsSaved"));
      setError(null);
      return true;
    } catch (reason) {
      setError(messageFor(reason, t));
      return false;
    }
  }

  async function testSettings(url?: string): Promise<void> {
    if (!selectedId) return;
    try {
      const result = await dashboardApi.testFeishu(selectedId, url);
      setNotice(result.success ? t("settings.testSuccess") : result.detail);
      setError(null);
    } catch (reason) {
      setError(messageFor(reason, t));
    }
  }

  async function refreshCurrent(): Promise<void> {
    if (!selectedId) return;
    setRefreshing(true);
    try {
      const [nextOverview, nextSettings] = await Promise.all([
        dashboardApi.getOverview(selectedId),
        dashboardApi.getSettings(selectedId),
      ]);
      setOverview(nextOverview);
      setSettings(nextSettings);
      setNotice(t("app.workspaceRefreshed"));
    } catch (reason) {
      setError(messageFor(reason, t));
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) return <div className="loading-screen"><LoaderCircle className="spin" size={25} /><span>{t("app.loading")}</span></div>;
  if (workspaces.length === 0) {
    return <><WorkspaceOnboarding onReady={(workspace) => void handleOnboardingReady(workspace)} onError={setError} />{error && <Notice type="error" message={error} closeLabel={t("app.close")} />}</>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-lockup-main">
            <img className="brand-logo" src="/lumon-mark.png" alt={t("app.brandAlt")} />
            <span className="brand-copy"><strong>Lumon</strong><small>{t("app.workspaceConsole")}</small></span>
          </div>
          <p className="sidebar-slogan">{t("app.slogan")}</p>
        </div>
        <nav className="side-nav" aria-label={t("app.dashboardSections")}>
          <button className={view === "overview" ? "active" : ""} type="button" onClick={() => changeView("overview")}><LayoutDashboard size={17} />{t("app.overview")}</button>
          <button className={view === "settings" ? "active" : ""} type="button" onClick={() => changeView("settings")}><Settings size={17} />{t("app.settings")}</button>
        </nav>
        <div className="sidebar-footer">
          <img className="company-logo" src="/inspire-group-logo-white.png" alt={t("app.companyLogoAlt")} />
          <span className="sidebar-version">v{appVersion ?? "—"}</span>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-context"><span className="topbar-label">{t("app.currentWorkspace")}</span><WorkspacePicker workspaces={workspaces} selectedId={selectedId} onChange={changeWorkspace} /></div>
          <div className="topbar-actions">
            <LanguagePicker />
            <span className="topbar-status"><span className="online-dot" />{t("app.localOnly")}</span>
          </div>
        </header>
        {error && <Notice type="error" message={error} onClose={() => setError(null)} closeLabel={t("app.close")} />}
        <main className="content-area">
          {selectedId && view === "overview" && overview && <WorkspaceOverview overview={overview} onRefresh={() => void refreshCurrent()} refreshing={refreshing} />}
          {selectedId && view === "settings" && settings && <SettingsPage settings={settings} onSave={saveSettings} onTest={testSettings} onDirtyChange={setSettingsDirty} />}
          {selectedId && refreshing && !overview && !settings && <div className="loading-inline"><LoaderCircle className="spin" size={22} />{t("app.readingWorkspace")}</div>}
        </main>
      </div>
      {notice && <Notice type="success" message={notice} />}
    </div>
  );
}

function Notice({ type, message, onClose, closeLabel }: { type: "success" | "error"; message: string; onClose?: () => void; closeLabel?: string }): React.JSX.Element {
  const Icon = type === "success" ? CheckCircle2 : AlertTriangle;
  return <div className={`notice notice-${type}`} role={type === "error" ? "alert" : "status"}>
    <Icon size={16} />
    <span>{message}</span>
    {onClose && <button className="notice-close" type="button" onClick={onClose} aria-label={closeLabel}><X size={15} /></button>}
  </div>;
}

function messageFor(reason: unknown, t: Translator): string {
  if (reason instanceof ApiError) return reason.message;
  return reason instanceof Error ? reason.message : t("app.dashboardRequestFailed");
}
