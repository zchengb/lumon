import {
  AlertTriangle,
  CheckCircle2,
  LayoutDashboard,
  LoaderCircle,
  Settings,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, dashboardApi } from "./api";
import { readNavigation, writeNavigation } from "./navigation";
import { SettingsPage } from "../features/settings/SettingsPage";
import { WorkspaceOnboarding } from "../features/workspaces/WorkspaceOnboarding";
import { WorkspaceOverview } from "../features/workspaces/WorkspaceOverview";
import { WorkspaceHealthLabel, WorkspacePicker } from "../features/workspaces/WorkspacePicker";
import { resolveWorkspaceSelection } from "../features/workspaces/workspaceSelection";
import type { SettingsUpdate, View, WorkspaceListItem, WorkspaceOverview as WorkspaceOverviewData, WorkspaceSettings } from "../shared/types";

export function App(): React.JSX.Element {
  const initialNavigation = readNavigation(window.location.search);
  const [workspaces, setWorkspaces] = useState<WorkspaceListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(initialNavigation.workspaceId);
  const [view, setView] = useState<View>(initialNavigation.view);
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
    void refreshWorkspaces().catch((reason: unknown) => setError(messageFor(reason))).finally(() => setLoading(false));
  }, [refreshWorkspaces]);

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
      .catch((reason: unknown) => { if (!cancelled) setError(messageFor(reason)); })
      .finally(() => { if (!cancelled) setRefreshing(false); });
    return () => { cancelled = true; };
  }, [selectedId]);

  useEffect(() => {
    window.history.replaceState(null, "", writeNavigation({ workspaceId: selectedId, view }));
  }, [selectedId, view]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 3500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const selectedWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.workspace_id === selectedId) ?? null,
    [selectedId, workspaces],
  );

  function changeWorkspace(nextId: string): void {
    if (settingsDirty && !window.confirm("当前配置尚未保存，确定要切换 Workspace 吗？")) return;
    setSettingsDirty(false);
    setSelectedId(nextId);
  }

  function changeView(nextView: View): void {
    if (nextView === view) return;
    if (settingsDirty && !window.confirm("当前配置尚未保存，确定要离开设置页吗？")) return;
    setSettingsDirty(false);
    setView(nextView);
  }

  async function handleOnboardingReady(workspace: WorkspaceListItem): Promise<void> {
    try {
      setWorkspaces(await dashboardApi.listWorkspaces());
      setSelectedId(workspace.workspace_id);
      setView("overview");
      setNotice(`Workspace「${workspace.name}」已准备完成。`);
      setError(null);
    } catch (reason) {
      setError(messageFor(reason));
    }
  }

  async function saveSettings(update: SettingsUpdate): Promise<boolean> {
    if (!selectedId) return false;
    try {
      const saved = await dashboardApi.updateSettings(selectedId, update);
      setSettings(saved);
      setNotice("飞书 Webhook 配置已保存。");
      setError(null);
      return true;
    } catch (reason) {
      setError(messageFor(reason));
      return false;
    }
  }

  async function testSettings(url?: string): Promise<void> {
    if (!selectedId) return;
    try {
      const result = await dashboardApi.testFeishu(selectedId, url);
      setNotice(result.detail);
      setError(null);
    } catch (reason) {
      setError(messageFor(reason));
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
      setNotice("Workspace 数据已刷新。");
    } catch (reason) {
      setError(messageFor(reason));
    } finally {
      setRefreshing(false);
    }
  }

  if (loading) return <div className="loading-screen"><LoaderCircle className="spin" size={25} /><span>正在加载 Lumon Dashboard…</span></div>;
  if (workspaces.length === 0) {
    return <><WorkspaceOnboarding onReady={(workspace) => void handleOnboardingReady(workspace)} onError={setError} />{error && <Notice type="error" message={error} />}</>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <img className="brand-logo" src="/lumon-mark.png" alt="Lumon" />
          <span className="brand-copy"><strong>Lumon</strong><small>Workspace console</small></span>
        </div>
        <div className="sidebar-section-label">当前 Workspace</div>
        <div className="sidebar-workspace">
          {selectedWorkspace && <>
            <div className="sidebar-workspace-top"><span>ACTIVE</span><WorkspaceHealthLabel health={selectedWorkspace.health} /></div>
            <strong>{selectedWorkspace.name}</strong>
            <code>{selectedWorkspace.path}</code>
          </>}
        </div>
        <nav className="side-nav" aria-label="Dashboard sections">
          <button className={view === "overview" ? "active" : ""} type="button" onClick={() => changeView("overview")}><LayoutDashboard size={17} />总览</button>
          <button className={view === "settings" ? "active" : ""} type="button" onClick={() => changeView("settings")}><Settings size={17} />配置</button>
        </nav>
        <div className="sidebar-footer"><span className="local-badge"><span className="online-dot" />本机服务</span><code>127.0.0.1</code></div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-context"><span className="topbar-label">Workspace</span><WorkspacePicker workspaces={workspaces} selectedId={selectedId} onChange={changeWorkspace} /></div>
          <div className="topbar-status"><span className="online-dot" />Local only</div>
        </header>
        {error && <Notice type="error" message={error} onClose={() => setError(null)} />}
        <main className="content-area">
          {selectedId && view === "overview" && overview && <WorkspaceOverview overview={overview} onRefresh={() => void refreshCurrent()} refreshing={refreshing} />}
          {selectedId && view === "settings" && settings && <SettingsPage settings={settings} onSave={saveSettings} onTest={testSettings} onDirtyChange={setSettingsDirty} />}
          {selectedId && refreshing && !overview && !settings && <div className="loading-inline"><LoaderCircle className="spin" size={22} />正在读取 Workspace…</div>}
        </main>
      </div>
      {notice && <Notice type="success" message={notice} />}
    </div>
  );
}

function Notice({ type, message, onClose }: { type: "success" | "error"; message: string; onClose?: () => void }): React.JSX.Element {
  const Icon = type === "success" ? CheckCircle2 : AlertTriangle;
  return <div className={`notice notice-${type}`} role={type === "error" ? "alert" : "status"}>
    <Icon size={16} />
    <span>{message}</span>
    {onClose && <button className="notice-close" type="button" onClick={onClose} aria-label="关闭"><X size={15} /></button>}
  </div>;
}

function messageFor(reason: unknown): string {
  if (reason instanceof ApiError) return reason.message;
  return reason instanceof Error ? reason.message : "Dashboard 请求失败，请稍后重试。";
}
