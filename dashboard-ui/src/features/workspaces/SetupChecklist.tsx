import { LoaderCircle, RefreshCw } from "lucide-react";
import { useI18n } from "../../shared/i18n";
import type { SetupReport } from "../../shared/types";

interface SetupChecklistProps {
  report: SetupReport | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
}

export function SetupChecklist({ report, loading, error, onRefresh }: SetupChecklistProps): React.JSX.Element {
  const { t } = useI18n();
  const states = {
    ready: t("setup.ready"), missing: t("setup.missing"), needs_login: t("setup.needsLogin"),
    incompatible: t("setup.incompatible"), error: t("setup.error"),
  };
  return <section className="setup-checklist" aria-label={t("setup.title")} aria-busy={loading}>
    <div className="setup-heading"><strong>{t("setup.title")}</strong><button type="button" className="button button-secondary" disabled={loading} onClick={onRefresh} aria-label={t("setup.refresh")}>
      {loading ? <LoaderCircle size={14} className="spin" /> : <RefreshCw size={14} />}{t("setup.refresh")}
    </button></div>
    {loading && !report && <p role="status">{t("setup.checking")}</p>}
    {error && <p role="alert">{error}</p>}
    {report && <ul>{report.checks.map((check) => <li key={check.name}>
      <div className="setup-check-state"><span>{({ gh: "GitHub CLI", codex: "Codex CLI", git: "Git" } as Record<string, string>)[check.name] ?? check.name}</span><span className={check.state === "ready" ? "setup-ready" : "setup-pending"}>{states[check.state]}</span></div>
      {check.state !== "ready" && <div className="setup-action">
        {check.action && (check.action.startsWith("https://") ? <a href={check.action} target="_blank" rel="noreferrer">{t("setup.installGuide")}</a> : <code>{check.action}</code>)}
        {check.documentation_url && !check.action?.startsWith("https://") && <a href={check.documentation_url} target="_blank" rel="noreferrer">{t("setup.installGuide")}</a>}
      </div>}
    </li>)}</ul>}
  </section>;
}
