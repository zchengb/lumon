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
        <h1>{t("autoDelivery.title")}</h1>
      </div>
    </div>
    <DeliveryHistoryPanel key={workspaceId} workspaceId={workspaceId} onError={onError} />
  </div>;
}
