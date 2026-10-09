import { useI18n } from "../../shared/i18n";
import { DeliveryHistoryPanel } from "./DeliveryHistoryPanel";

export function AutoDeliveryPage({ workspaceId, onError }: {
  workspaceId: string;
  onError: (message: string | null) => void;
}): React.JSX.Element {
  const { t } = useI18n();
  return <div className="page-stack">
    <div className="page-heading">
      <div>
        <p className="eyebrow">{t("autoDelivery.eyebrow")}</p>
        <h1>{t("autoDelivery.title")}</h1>
        <p className="muted">{t("autoDelivery.subtitle")}</p>
      </div>
    </div>
    <DeliveryHistoryPanel key={workspaceId} workspaceId={workspaceId} onError={onError} />
  </div>;
}
