import { Container, Monitor, RefreshCw, Smartphone } from "lucide-react";
import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { VisualEnvironmentSnapshot } from "../../shared/types";
import { HelpTooltip } from "../shared/HelpTooltip";
import "./VisualEnvironmentPanel.css";

const platformNames = { ios: "iOS Simulator", android: "Android Emulator", web: "Web", docker: "Docker" };
const checkNames: Record<string, string> = {
  xcode: "Xcode / simctl", ios_runtime: "iOS Runtime", ios_device: "iOS Simulator",
  android_sdk: "Android SDK", adb: "ADB", emulator: "Android Emulator",
  acceleration: "CPU acceleration", android_avd: "AVD / System image",
  browser: "Chrome / Chromium", docker_engine: "Docker Engine",
};

export function VisualEnvironmentPanel({ workspaceId, refreshToken }: {
  workspaceId: string; refreshToken: object;
}): React.JSX.Element {
  const { t } = useI18n();
  const [revision, setRevision] = useState(0);
  const [snapshot, setSnapshot] = useState<VisualEnvironmentSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    setSnapshot(null);
    void dashboardApi.getVisualEnvironment(workspaceId, revision > 0).then((next) => {
      if (active) setSnapshot(next);
    }).catch(() => { if (active) setFailed(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [workspaceId, refreshToken, revision]);

  return <section className="panel visual-environment" aria-labelledby="visual-environment-title" aria-busy={loading}>
    <div className="panel-heading">
      <div className="field-label-heading">
        <h2 id="visual-environment-title">{t("environment.title")}</h2>
        <HelpTooltip helpId="visual-environment-help" label={t("environment.title")} help={t("environment.help")} />
      </div>
      <button type="button" className="button button-secondary" disabled={loading} onClick={() => setRevision(revision + 1)}>
        <RefreshCw size={15} className={loading ? "spin" : ""} />{t("environment.check")}
      </button>
    </div>
    {loading && <p className="empty-inline" role="status">{t("environment.loading")}</p>}
    {failed && <p className="empty-inline" role="status">{t("environment.failed")}</p>}
    {snapshot && (
      <div className="visual-environment-grid">
        {snapshot.environments.map((item) => {
          const Icon = item.platform === "docker" ? Container : item.platform === "web" ? Monitor : Smartphone;
          const help = item.checks.map((check) => `${checkNames[check.name] ?? check.name}: ${t(`environment.${check.status}`)}`).join("\n");
          return <div className="visual-environment-item" key={item.platform}>
            <div className="visual-environment-label"><Icon size={18} aria-hidden="true" />
              <strong>{platformNames[item.platform]}</strong>
              <HelpTooltip helpId={`environment-${item.platform}-help`} label={platformNames[item.platform]} help={help} />
            </div>
            <span className={`visual-environment-status visual-environment-${item.status}`}>{t(`environment.${item.status}`)}</span>
          </div>;
        })}
      </div>
    )}
  </section>;
}
