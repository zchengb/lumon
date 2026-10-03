import { LoaderCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { dashboardApi } from "../../app/api";
import { useI18n } from "../../shared/i18n";
import type { AgentModel } from "../../shared/types";

interface AgentModelPickerProps {
  model: string;
  reasoningEffort: string;
  onChange: (model: string, reasoningEffort: string) => void;
}

export function AgentModelPicker({ model, reasoningEffort, onChange }: AgentModelPickerProps): React.JSX.Element {
  const { t } = useI18n();
  const [models, setModels] = useState<AgentModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [refreshVersion, setRefreshVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setFailed(false);
    void dashboardApi.listAgentModels().then((catalog) => {
      if (active) setModels(catalog);
    }).catch(() => {
      if (active) setFailed(true);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [refreshVersion]);

  const selected = models.find((choice) => choice.model === model);
  const efforts = selected?.supported_reasoning_efforts ?? [reasoningEffort];

  function selectModel(modelId: string): void {
    const choice = models.find((item) => item.model === modelId);
    const nextEffort = choice && !choice.supported_reasoning_efforts.includes(reasoningEffort)
      ? choice.default_reasoning_effort
      : reasoningEffort;
    onChange(modelId, nextEffort);
  }

  return <>
    <div>
      <label className="field-label" htmlFor="agent-model">{t("agent.model")}</label>
      <div className="model-picker-controls">
        <select id="agent-model" className="text-input" value={model} onChange={(event) => selectModel(event.target.value)} aria-describedby="agent-model-help">
          {!selected && <option value={model}>{model}</option>}
          {models.map((choice) => <option key={choice.model} value={choice.model}>{choice.display_name}</option>)}
        </select>
        <button className="button button-secondary button-icon" type="button" aria-label={t("agent.refreshModels")} title={t("agent.refreshModels")} disabled={loading} onClick={() => setRefreshVersion((previous) => previous + 1)}>
          {loading ? <LoaderCircle size={16} className="spin" /> : <RefreshCw size={16} />}
        </button>
      </div>
      <p id="agent-model-help" className={`field-help ${failed ? "model-picker-error" : ""}`} role={failed ? "alert" : "status"}>
        {loading ? t("agent.modelsLoading") : failed ? t("agent.modelsFailed") : selected ? selected.description || t("agent.modelsSource") : t("agent.modelRetained")}
      </p>
    </div>
    <div>
      <label className="field-label" htmlFor="agent-reasoning">{t("agent.reasoning")}</label>
      <select id="agent-reasoning" className="text-input" value={reasoningEffort} onChange={(event) => onChange(model, event.target.value)}>
        {!efforts.includes(reasoningEffort) && <option value={reasoningEffort}>{reasoningEffort}</option>}
        {efforts.map((effort) => <option key={effort} value={effort}>{effort}</option>)}
      </select>
    </div>
  </>;
}
