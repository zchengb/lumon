import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { CodexCliStatus } from "../../shared/types";

export function CodexCliNotice({ modelRefresh }: { modelRefresh: number }): React.JSX.Element | null {
  const { t } = useI18n();
  const [status, setStatus] = useState<CodexCliStatus | null>(null);

  useEffect(() => {
    let active = true;
    setStatus(null);
    void dashboardApi.getCodexCliStatus(modelRefresh > 0).then((nextStatus) => {
      if (active) setStatus(nextStatus);
    }).catch(() => {
      if (active) setStatus(null);
    });
    return () => { active = false; };
  }, [modelRefresh]);

  if (status?.status !== "update_available" || !status.installed_version) return null;

  return <span className="codex-cli-notice" role="status">
    <code>{status.installed_version}</code>
    <span className="codex-cli-state">{t("agent.cli.update_available")}</span>
  </span>;
}
