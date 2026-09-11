import { FolderOpen, FolderPlus, GitBranch, LoaderCircle, Plus } from "lucide-react";
import { useState } from "react";
import { dashboardApi } from "../../app/api";
import { LanguagePicker, useI18n } from "../../shared/i18n";
import type { WorkspaceListItem } from "../../shared/types";

interface WorkspaceOnboardingProps {
  onReady: (workspace: WorkspaceListItem) => void;
  onError: (message: string) => void;
}

type OnboardingMode = "initialize" | "register";

export function WorkspaceOnboarding({ onReady, onError }: WorkspaceOnboardingProps): React.JSX.Element {
  const { t } = useI18n();
  const [mode, setMode] = useState<OnboardingMode>("initialize");
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [repositories, setRepositories] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [pickingFolder, setPickingFolder] = useState(false);

  async function chooseFolder(): Promise<void> {
    setPickingFolder(true);
    try {
      const selection = await dashboardApi.selectWorkspaceFolder();
      if (selection.path) setPath(selection.path);
    } catch (error) {
      onError(error instanceof Error ? error.message : t("onboarding.folderSelectionFailed"));
    } finally {
      setPickingFolder(false);
    }
  }

  async function submit(): Promise<void> {
    const normalizedPath = path.trim();
    if (!normalizedPath) {
      onError(t("onboarding.pathRequired"));
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "register") {
        onReady(await dashboardApi.registerWorkspace(normalizedPath));
      } else {
        const response = await dashboardApi.initializeWorkspace({
          path: normalizedPath,
          ...(name.trim() ? { name: name.trim() } : {}),
          repositories: repositories.split("\n").map((value) => value.trim()).filter(Boolean),
        });
        const workspaces = await dashboardApi.listWorkspaces();
        const created = workspaces.find((item) => item.workspace_id === response.workspace_id);
        if (!created) throw new Error(t("onboarding.reloadFailed"));
        onReady(created);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : t("onboarding.operationFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="onboarding-wrap">
      <section className="onboarding-card">
        <LanguagePicker className="onboarding-language" />
        <div className="onboarding-brand"><img className="onboarding-logo" src="/lumon-mark.png" alt={t("app.brandAlt")} /><div><strong>Lumon</strong><span>{t("app.workspaceConsole")}</span></div></div>
        <p className="eyebrow">{t("onboarding.localEyebrow")}</p>
        <h1>{t("onboarding.title")}</h1>
        <p className="onboarding-copy">{t("onboarding.copy")}</p>

        <div className="segmented-control" role="tablist" aria-label={t("onboarding.operationAria")}>
          <button className={mode === "initialize" ? "active" : ""} type="button" role="tab" aria-selected={mode === "initialize"} onClick={() => setMode("initialize")}>
            <FolderPlus size={16} />{t("onboarding.initializeNew")}
          </button>
          <button className={mode === "register" ? "active" : ""} type="button" role="tab" aria-selected={mode === "register"} onClick={() => setMode("register")}>
            <Plus size={16} />{t("onboarding.addExisting")}
          </button>
        </div>

        <label className="field-label" htmlFor="workspace-path">{t("onboarding.workspacePath")}</label>
        <div className="path-picker">
          <input id="workspace-path" className="text-input" value={path} onChange={(event) => setPath(event.target.value)} placeholder={t("onboarding.workspacePathPlaceholder")} />
          <button className="button button-secondary path-picker-button" type="button" onClick={() => void chooseFolder()} disabled={submitting || pickingFolder} aria-label={t("onboarding.chooseFolderAria")}>
            {pickingFolder ? <LoaderCircle size={16} className="spin" /> : <FolderOpen size={16} />}
            {pickingFolder ? t("onboarding.processing") : t("onboarding.chooseFolder")}
          </button>
        </div>

        {mode === "initialize" && (
          <>
            <label className="field-label" htmlFor="workspace-name">{t("onboarding.nameOptional")}</label>
            <input id="workspace-name" className="text-input" value={name} onChange={(event) => setName(event.target.value)} placeholder={t("onboarding.namePlaceholder")} />
            <label className="field-label" htmlFor="workspace-repositories">{t("onboarding.repositoryUrlOptional")}</label>
            <textarea id="workspace-repositories" className="text-input text-area" value={repositories} onChange={(event) => setRepositories(event.target.value)} placeholder={t("onboarding.repositoryPlaceholder")} rows={3} />
            <p className="field-help"><GitBranch size={14} />{t("onboarding.authHelp")}</p>
          </>
        )}

        <button className="button button-primary button-wide" type="button" onClick={() => void submit()} disabled={submitting}>
          {submitting ? <LoaderCircle size={17} className="spin" /> : mode === "initialize" ? <FolderPlus size={17} /> : <Plus size={17} />}
          {submitting ? t("onboarding.processing") : mode === "initialize" ? t("onboarding.initializeAction") : t("onboarding.addAction")}
        </button>
      </section>
    </main>
  );
}
