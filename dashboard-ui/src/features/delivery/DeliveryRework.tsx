import { ArrowRight, Check, LoaderCircle, RotateCcw } from "lucide-react";
import { useI18n } from "../../shared/i18n";
import type { DeliveryActivity, DeliveryRun } from "../../shared/types";

export function deliveryReworks(activity: DeliveryActivity[]): DeliveryActivity[] {
  // shortcut: counts retained phase events only; persist a counter if lifetime totals are needed.
  const returns: DeliveryActivity[] = [];
  let previousPhase = "";
  for (const event of activity) {
    if (event.command || event.operation_id || event.exit_code != null || event.detail.startsWith("command execution:")) continue;
    if (!["discover", "claim", "implementation", "verification", "handoff", "publish"].includes(event.phase)) continue;
    if (previousPhase === "verification" && event.phase === "implementation") returns.push(event);
    previousPhase = event.phase;
  }
  return returns;
}

export function DeliveryRework({ run, reworks, timeLabel }: {
  run: DeliveryRun; reworks: DeliveryActivity[]; timeLabel: (timestamp: string) => string;
}): React.JSX.Element | null {
  const { t } = useI18n();
  if (!reworks.length) return null;
  const running = run.state === "running";
  const fixing = run.phase === "implementation";
  const verified = run.state === "completed" || ["handoff", "publish"].includes(run.phase);
  const stopped = run.state === "failed" || run.state === "blocked" || run.state === "stopped";
  let developTone = "";
  let verifyTone = "";
  if (!fixing) developTone = "is-complete";
  else if (running) developTone = "is-current";
  else if (stopped) developTone = "is-stopped";
  if (verified) verifyTone = "is-complete";
  else if (run.phase === "verification" && running) verifyTone = "is-current";
  else if (run.phase === "verification" && stopped) verifyTone = "is-stopped";
  return <section className="delivery-rework" aria-label={t("autoDelivery.rework")}>
    <div className="delivery-rework-heading">
      <RotateCcw size={16} aria-hidden="true" />
      <strong>{t("autoDelivery.reworkCount", { count: reworks.length })}</strong>
      {running && (fixing || run.phase === "verification") && <span className="status-pill status-warning" role="status">
        {fixing ? t("autoDelivery.reworking") : t("autoDelivery.verificationRound", { round: reworks.length + 1 })}
      </span>}
    </div>
    <ol className="delivery-rework-path" aria-label={t("autoDelivery.rework")}>
      <li className="is-returned"><RotateCcw size={13} aria-hidden="true" />{t("autoDelivery.stage.verification")}<ArrowRight size={13} aria-hidden="true" /></li>
      <li className={developTone}>
        {running && fixing ? <LoaderCircle size={13} className="spin" aria-hidden="true" /> : !fixing && <Check size={13} aria-hidden="true" />}
        {t("autoDelivery.stage.implementation")}<ArrowRight size={13} aria-hidden="true" />
      </li>
      <li className={verifyTone}>
        {verified ? <Check size={13} aria-hidden="true" /> : running && run.phase === "verification" && <LoaderCircle size={13} className="spin" aria-hidden="true" />}
        {t("autoDelivery.verifyAgain")}
      </li>
    </ol>
    <details className="delivery-rework-history">
      <summary>{t("autoDelivery.reworkHistory")}</summary>
      <ol>{reworks.map((event, index) => <li key={`${event.at}-${index}`}>
        <time dateTime={event.at}>{timeLabel(event.at)}</time><p>{event.detail}</p>
      </li>)}</ol>
    </details>
  </section>;
}
