import {
  AlertTriangle,
  Bot,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  GitBranch,
  LayoutDashboard,
  LoaderCircle,
  Puzzle,
  Rocket,
  ScanSearch,
  Settings,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ApiError, dashboardApi } from "./api";
import { readNavigation, writeNavigation } from "./navigation";
import { AgentSettingsPage } from "../features/agent/AgentSettingsPage";
import { ChatHistoryPage } from "../features/agent/ChatHistoryPage";
import { AutoDeliveryPage } from "../features/delivery/AutoDeliveryPage";
import { AutoScanPage } from "../features/scan/AutoScanPage";
import { CapabilitiesPage } from "../features/capabilities/CapabilitiesPage";
import { FlowsPage } from "../features/flows/FlowsPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { WorkspaceOnboarding } from "../features/workspaces/WorkspaceOnboarding";
import { WorkspaceOverview } from "../features/workspaces/WorkspaceOverview";
import { WorkspacePicker } from "../features/workspaces/WorkspacePicker";
import { resolveWorkspaceSelection } from "../features/workspaces/workspaceSelection";
import { LanguagePicker, useI18n, type Translator } from "../shared/i18n";
import type {
  AgentSettings,
  AgentSettingsUpdate,
  SettingsUpdate,
  View,
  WorkspaceListItem,
  WorkspaceOverview as WorkspaceOverviewData,
  WorkspaceSettings,
} from "../shared/types";

export function App(): React.JSX.Element {
  const { t } = useI18n();
  const initialNavigation = readNavigation(window.location.search);
  const [workspaces, setWorkspaces] = useState<WorkspaceListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialNavigation.workspaceId);
  const [view, setView] = useState<View>(initialNavigation.view);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const [overview, setOverview] = useState<WorkspaceOverviewData | null>(null);
  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [agentSettings, setAgentSettings] = useState<AgentSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [settingsDirty, setSettingsDirty] = useState(false);
  const [agentSettingsDirty, setAgentSettingsDirty] = useState(false);
  const [autoDeliveryDirty, setAutoDeliveryDirty] = useState(false);
  const [autoScanDirty, setAutoScanDirty] = useState(false);
  const [flowsDirty, setFlowsDirty] = useState(false);
  const [capabilitiesDirty, setCapabilitiesDirty] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const viewLabels: Record<View, string> = {
    overview: t("app.overview"),
    settings: t("app.settings"),
    agent: t("app.agentSettings"),
    "auto-delivery": t("app.autoDelivery"),
    "auto-scan": t("app.autoScan"),
    flows: t("app.flows"),
    capabilities: t("app.capabilities"),
  };

  const refreshWorkspaces = useCallback(async (): Promise<WorkspaceListItem[]> => {
    const next = await dashboardApi.listWorkspaces();
    setWorkspaces(next);
    setSelectedId((current) => resolveWorkspaceSelection(current, initialNavigation.workspaceId, next));
    return next;
  }, [initialNavigation.workspaceId]);

  useEffect(() => {
    void Promise.all([refreshWorkspaces(), dashboardApi.getBootstrap(), dashboardApi.getAgentSettings()])
      .then(([, bootstrap, nextAgentSettings]) => {
        setAppVersion(bootstrap.version);
        setAgentSettings(nextAgentSettings);
      })
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
    if (
      (settingsDirty || agentSettingsDirty || autoDeliveryDirty || autoScanDirty || flowsDirty || capabilitiesDirty)
      && !window.confirm(t("app.unsavedWorkspaceConfirm"))
    ) return;
    setSettingsDirty(false);
    setAgentSettingsDirty(false);
    setAutoDeliveryDirty(false);
    setAutoScanDirty(false);
    setFlowsDirty(false);
    setCapabilitiesDirty(false);
    setSelectedId(nextId);
  }

  function changeView(nextView: View): void {
    if (nextView === view) return;
    const currentViewDirty = view === "settings"
      ? settingsDirty || agentSettingsDirty
        : view === "auto-delivery"
          ? autoDeliveryDirty
        : view === "auto-scan"
          ? autoScanDirty
        : view === "flows"
          ? flowsDirty
          : view === "capabilities"
            ? capabilitiesDirty
          : false;
    if (currentViewDirty && !window.confirm(t("app.unsavedViewConfirm"))) return;
    setSettingsDirty(false);
    setAgentSettingsDirty(false);
    setAutoDeliveryDirty(false);
    setAutoScanDirty(false);
    setFlowsDirty(false);
    setCapabilitiesDirty(false);
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

  async function saveAgentSettings(update: AgentSettingsUpdate): Promise<boolean> {
    try {
      const saved = await dashboardApi.updateAgentSettings(update);
      setAgentSettings(saved);
      setNotice(t("app.agentSettingsSaved"));
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
      setAgentSettings(await dashboardApi.getAgentSettings());
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
    <div className={`app-shell${sidebarCollapsed ? " sidebar-is-collapsed" : ""}`}>
      <aside className="sidebar" id="dashboard-navigation">
        <div className="brand-lockup">
          <div className="brand-lockup-main">
            <img className="brand-logo" src="/lumon-mark.png" alt={t("app.brandAlt")} />
            <div className="brand-copy">
              <strong>Lumon</strong>
              <small>{t("app.slogan")}</small>
            </div>
          </div>
        </div>
        <nav className="side-nav" aria-label={t("app.dashboardSections")}>
          <p className="nav-group-label">{t("app.workspaceGroup")}</p>
          <button className={view === "overview" ? "active" : ""} title={viewLabels.overview} aria-label={viewLabels.overview} aria-current={view === "overview" ? "page" : undefined} type="button" onClick={() => changeView("overview")}><LayoutDashboard size={17} /><span>{viewLabels.overview}</span></button>
          <button className={view === "settings" ? "active" : ""} title={viewLabels.settings} aria-label={viewLabels.settings} aria-current={view === "settings" ? "page" : undefined} type="button" onClick={() => changeView("settings")}><Settings size={17} /><span>{viewLabels.settings}</span></button>
          <button className={view === "agent" ? "active" : ""} title={viewLabels.agent} aria-label={viewLabels.agent} aria-current={view === "agent" ? "page" : undefined} type="button" onClick={() => changeView("agent")}><Bot size={17} /><span>{viewLabels.agent}</span></button>
          <p className="nav-group-label">{t("app.automationGroup")}</p>
          <button className={view === "auto-delivery" ? "active" : ""} title={viewLabels["auto-delivery"]} aria-label={viewLabels["auto-delivery"]} aria-current={view === "auto-delivery" ? "page" : undefined} type="button" onClick={() => changeView("auto-delivery")}><Rocket size={17} /><span>{viewLabels["auto-delivery"]}</span></button>
          <button className={view === "auto-scan" ? "active" : ""} title={viewLabels["auto-scan"]} aria-label={viewLabels["auto-scan"]} aria-current={view === "auto-scan" ? "page" : undefined} type="button" onClick={() => changeView("auto-scan")}><ScanSearch size={17} /><span>{viewLabels["auto-scan"]}</span></button>
          <p className="nav-group-label">{t("app.libraryGroup")}</p>
          <button className={view === "flows" ? "active" : ""} title={viewLabels.flows} aria-label={viewLabels.flows} aria-current={view === "flows" ? "page" : undefined} type="button" onClick={() => changeView("flows")}><GitBranch size={17} /><span>{viewLabels.flows}</span></button>
          <button className={view === "capabilities" ? "active" : ""} title={viewLabels.capabilities} aria-label={viewLabels.capabilities} aria-current={view === "capabilities" ? "page" : undefined} type="button" onClick={() => changeView("capabilities")}><Puzzle size={17} /><span>{viewLabels.capabilities}</span></button>
        </nav>
        <div className="sidebar-footer">
          <img className="company-logo" src="/inspire-group-logo-white.png" alt={t("app.companyLogoAlt")} />
          <span className="sidebar-version">v{appVersion ?? "—"}</span>
        </div>
      </aside>
      <button
        className="sidebar-toggle"
        type="button"
        onClick={() => setSidebarCollapsed((value) => !value)}
        aria-expanded={!sidebarCollapsed}
        aria-controls="dashboard-navigation"
        aria-label={sidebarCollapsed ? t("app.expandNavigation") : t("app.collapseNavigation")}
        title={sidebarCollapsed ? t("app.expandNavigation") : t("app.collapseNavigation")}
      >{sidebarCollapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}</button>

      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-page"><span>{t("app.workspaceConsole")}</span><ChevronRight size={14} aria-hidden="true" /><strong>{viewLabels[view]}</strong></div>
          <div className="topbar-actions">
            <LanguagePicker />
            <div className="topbar-context"><span className="topbar-label">{t("app.currentWorkspace")}</span><WorkspacePicker workspaces={workspaces} selectedId={selectedId} onChange={changeWorkspace} /></div>
          </div>
        </header>
        {error && <Notice type="error" message={error} onClose={() => setError(null)} closeLabel={t("app.close")} />}
        <main className="content-area">
          {selectedId && view === "overview" && overview && <WorkspaceOverview overview={overview} settings={settings} onNavigate={changeView} onRefresh={() => void refreshCurrent()} refreshing={refreshing} />}
          {selectedId && view === "settings" && settings && <div className="page-stack">
            <SettingsPage settings={settings} onSave={saveSettings} onTest={testSettings} onDirtyChange={setSettingsDirty} />
            {agentSettings && <AgentSettingsPage key={selectedId} settings={agentSettings} workspaces={workspaces} onSave={saveAgentSettings} onDirtyChange={setAgentSettingsDirty} />}
          </div>}
          {selectedId && view === "agent" && <ChatHistoryPage key={selectedId} workspaceId={selectedId} />}
          {selectedId && view === "auto-delivery" && settings && <AutoDeliveryPage settings={settings} onSave={saveSettings} onDirtyChange={setAutoDeliveryDirty} />}
          {selectedId && view === "auto-scan" && settings && <AutoScanPage workspaceId={selectedId} settings={settings} onSave={saveSettings} onDirtyChange={setAutoScanDirty} onError={setError} />}
          {selectedId && view === "flows" && <FlowsPage workspaceId={selectedId} onDirtyChange={setFlowsDirty} onNotice={setNotice} onError={setError} />}
          {selectedId && view === "capabilities" && <CapabilitiesPage workspaceId={selectedId} onDirtyChange={setCapabilitiesDirty} onNotice={setNotice} onError={setError} />}
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
