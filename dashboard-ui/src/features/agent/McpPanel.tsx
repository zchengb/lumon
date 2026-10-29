import { Plug, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { McpDiscovery, McpInventory, McpServer } from "../../shared/types";
import { HelpTooltip } from "../shared/HelpTooltip";
import "./McpPanel.css";

export function McpPanel({ workspaceId }: { workspaceId: string }): React.JSX.Element {
  const { t } = useI18n();
  const [inventory, setInventory] = useState<McpInventory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, McpDiscovery>>({});
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [transport, setTransport] = useState<"stdio" | "http">("http");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [url, setUrl] = useState("");
  const [tokenEnv, setTokenEnv] = useState("");
  const requestNumber = useRef(0);

  async function refresh(): Promise<void> {
    const number = ++requestNumber.current;
    setLoading(true);
    try {
      const next = await dashboardApi.listMcp(workspaceId);
      if (number === requestNumber.current) { setInventory(next); setError(false); }
    } catch {
      if (number === requestNumber.current) setError(true);
    } finally {
      if (number === requestNumber.current) setLoading(false);
    }
  }

  useEffect(() => {
    setInventory(null);
    setDetails({});
    void refresh();
    return () => { requestNumber.current += 1; };
  }, [workspaceId]);

  async function mutate(key: string, operation: () => Promise<void>): Promise<void> {
    if (busy !== null) return;
    setBusy(key);
    setError(false);
    try {
      await operation();
      setDetails({});
      await refresh();
    } catch {
      await refresh();
      setError(true);
    }
    finally { setBusy(null); }
  }

  async function discover(serverName: string): Promise<void> {
    if (busy !== null) return;
    setBusy(serverName);
    try {
      const result = await dashboardApi.discoverMcp(workspaceId, serverName);
      setDetails((previous) => ({ ...previous, [serverName]: result }));
    } catch {
      setDetails((previous) => ({ ...previous, [serverName]: { failed: true, tools: [], total_tools: 0, description: null, auth_status: "unknown", runtime_status: null } }));
    } finally { setBusy(null); }
  }

  const servers = inventory?.servers ?? [];
  const enabled = servers.filter((server) => server.enabled).length;
  function authLabel(auth: string): string {
    if (auth === "notLoggedIn" || auth === "not_logged_in") return t("mcp.authRequired");
    if (auth === "oAuth" || auth === "oauth") return t("mcp.authOAuth");
    if (auth === "bearerToken" || auth === "bearer_token") return t("mcp.authBearer");
    return t("mcp.authUnknown");
  }
  function discoveryLabel(result: McpDiscovery): string {
    if (result.runtime_status === "authenticationRequired" || result.auth_status === "notLoggedIn" || result.auth_status === "not_logged_in") return t("mcp.authRequired");
    if (result.failed) return t("mcp.checkFailed");
    return result.runtime_status === "connected" ? t("mcp.connected") : t("mcp.catalogReady");
  }
  function descriptionFor(server: McpServer): string | null {
    const provided = details[server.name]?.description;
    if (provided) return provided;
    switch (server.description_kind) {
      case "figma": return t("mcp.descriptionFigma");
      case "codex_app": return t("mcp.descriptionCodexApp");
      case "computer_use": return t("mcp.descriptionComputerUse");
      case "cua_repl": return t("mcp.descriptionCua");
      case "node_repl": return t("mcp.descriptionNode");
      default: return null;
    }
  }
  return <section id="mcp-manager" className="panel mcp-panel" aria-labelledby="mcp-title-manage" aria-busy={loading || busy !== null}>
    <div className="panel-heading">
      <div className="field-label-heading"><Plug size={18} aria-hidden="true" /><h2 id="mcp-title-manage">{t("mcp.title")}</h2>
        <HelpTooltip helpId="mcp-help" label={t("mcp.title")} help={t("mcp.help")} />
      </div>
      <div className="mcp-heading-actions">
        {inventory && <span className="mcp-count">{t("mcp.count", { enabled, total: servers.length })}</span>}
        <button type="button" className="button button-secondary" onClick={() => void refresh()} disabled={loading || busy !== null}><RefreshCw size={15} />{t("mcp.refresh")}</button>
      </div>
    </div>
    {loading && !inventory && <p className="empty-inline" role="status">{t("mcp.loading")}</p>}
    {error && <p className="empty-inline mcp-error" role="alert">{inventory ? t("mcp.actionFailed") : t("mcp.unavailable")}</p>}
    {inventory && <>
      {servers.length === 0 ? <p className="empty-inline">{t("mcp.empty")}</p> : <ul className="mcp-list">
        {servers.map((server) => <li key={server.name} className="mcp-row">
          <div className="mcp-row-main"><div className="mcp-row-title"><strong>{server.source === "workspace" ? "GitHub MCP" : server.name}</strong><span className={`mcp-state ${server.enabled ? "is-enabled" : ""}`}>{server.enabled ? t("settings.enabled") : t("settings.disabled")}</span>
            <small>{server.transport.toUpperCase()} · {t(server.source === "workspace" ? "mcp.workspaceReadOnly" : server.source === "user" ? "mcp.user" : server.source === "project" ? "mcp.project" : "mcp.other")}{server.workspace_host && ` · ${server.workspace_host}`}{server.transport === "http" && ` · ${authLabel(details[server.name]?.auth_status ?? server.auth_status)}`}</small></div>
            {descriptionFor(server) && <small className="mcp-description">{descriptionFor(server)}</small>}
          </div>
          <div className="mcp-row-actions">
            <button type="button" className="button button-secondary" onClick={() => void discover(server.name)} disabled={!server.enabled || busy !== null}>{busy === server.name ? t("mcp.checking") : t("mcp.check")}</button>
            <label className={`settings-toggle ${server.enabled ? "is-enabled" : ""}`} title={server.source === "workspace" ? t("mcp.workspaceReadOnly") : server.manageable ? undefined : t("mcp.readOnly")}>
              <input type="checkbox" role="switch" aria-label={t("mcp.toggle", { name: server.name })} checked={server.enabled} disabled={server.source === "workspace" || !server.manageable || !inventory.user_version || busy !== null} onChange={(event) => { const checked = event.target.checked; void mutate(server.name, () => dashboardApi.setMcpEnabled(workspaceId, server.name, checked, inventory.user_version)); }} />
              <span className="settings-switch" aria-hidden="true"><span className="settings-switch-thumb" /></span>
            </label>
            <button type="button" className="button button-secondary mcp-remove" aria-label={`${t("mcp.remove")} ${server.name}`} title={server.source === "workspace" ? t("mcp.workspaceReadOnly") : server.manageable ? t("mcp.remove") : t("mcp.readOnly")} disabled={server.source === "workspace" || !server.manageable || !inventory.user_version || busy !== null} onClick={() => { if (window.confirm(t("mcp.confirmRemove", { name: server.name }))) void mutate(server.name, () => dashboardApi.removeMcp(workspaceId, server.name, inventory.user_version)); }}><Trash2 size={15} /></button>
          </div>
          {details[server.name] && <div className="mcp-discovery" role="status">
            {discoveryLabel(details[server.name])}
            {!details[server.name].failed && <div><strong>{t("mcp.tools")}{details[server.name].total_tools > details[server.name].tools.length ? ` (${details[server.name].tools.length}/${details[server.name].total_tools})` : ""}: </strong>{details[server.name].tools.length ? details[server.name].tools.join(", ") : t("mcp.noTools")}</div>}
          </div>}
        </li>)}
      </ul>}
      <div className="mcp-add-area">
        {!inventory.user_version && <p className="mcp-error">{t("mcp.versionUnavailable")}</p>}
        {!adding ? <button type="button" className="button button-secondary" disabled={!inventory.user_version || busy !== null} onClick={() => setAdding(true)}><Plus size={15} />{t("mcp.add")}</button>
          : <form className="mcp-form" onSubmit={(event) => {
            event.preventDefault();
            void mutate("add", async () => {
              await dashboardApi.addMcp(workspaceId, { name: name.trim(), transport, ...(transport === "http" ? { url: url.trim(), bearer_token_env_var: tokenEnv.trim() || undefined } : { command: command.trim(), args: args.split(/\r?\n/).filter((arg) => arg.length > 0) }), expected_version: inventory.user_version });
              setAdding(false); setName(""); setCommand(""); setArgs(""); setUrl(""); setTokenEnv("");
            });
          }}>
            <label>{t("mcp.name")}<input className="text-input" value={name} onChange={(event) => setName(event.target.value)} required pattern="[A-Za-z0-9_-]{1,64}" /></label>
            <label>{t("mcp.transport")}<select className="text-input" value={transport} onChange={(event) => setTransport(event.target.value as "stdio" | "http")}><option value="http">HTTP</option><option value="stdio">STDIO</option></select></label>
            {transport === "http" ? <><div className="mcp-form-wide"><div className="field-label-heading"><label htmlFor="mcp-url">{t("mcp.url")}</label><HelpTooltip helpId="mcp-url-help" label={t("mcp.url")} help={t("mcp.urlHelp")} /></div><input id="mcp-url" className="text-input" type="url" value={url} onChange={(event) => setUrl(event.target.value)} required /></div><label className="mcp-form-wide">{t("mcp.tokenEnv")}<input className="text-input" value={tokenEnv} onChange={(event) => setTokenEnv(event.target.value)} pattern="[A-Za-z_][A-Za-z0-9_]*" /></label></>
              : <><label className="mcp-form-wide">{t("mcp.command")}<input className="text-input" value={command} onChange={(event) => setCommand(event.target.value)} required /></label><label className="mcp-form-wide">{t("mcp.args")}<textarea className="text-input" value={args} onChange={(event) => setArgs(event.target.value)} rows={3} /></label></>}
            <div className="mcp-form-wide mcp-form-actions"><button className="button button-primary" type="submit" disabled={busy !== null}>{t("mcp.save")}</button><button className="button button-secondary" type="button" onClick={() => setAdding(false)} disabled={busy !== null}>{t("mcp.cancel")}</button></div>
          </form>}
      </div>
    </>}
  </section>;
}
