import { useI18n } from "../../shared/i18n";
import type { ScanRun } from "../../shared/types";

export function ScanFailureDetails({ run, expanded = false }: {
  run: ScanRun;
  expanded?: boolean;
}): React.JSX.Element | null {
  const { t } = useI18n();
  const failures = run.failures.filter((reason) => reason.trim());
  const unsuccessful = run.state === "failed" || run.state === "completed_with_failures";
  if (!failures.length && !unsuccessful) return null;

  return <details className={`scan-failure-details ${run.state === "failed" ? "is-failed" : ""}`} open={expanded}>
    <summary>{t("autoScan.failureDetails")}</summary>
    {failures.length ? <ul>{failures.map((reason, index) => <li key={index}>{reason}</li>)}</ul>
      : <p>{t("autoScan.failureReasonUnavailable")}</p>}
  </details>;
}
