import { FolderPlus, GitBranch, LoaderCircle, Plus, Sparkles } from "lucide-react";
import { useState } from "react";
import { dashboardApi } from "../../app/api";
import type { WorkspaceListItem } from "../../shared/types";

interface WorkspaceOnboardingProps {
  onReady: (workspace: WorkspaceListItem) => void;
  onError: (message: string) => void;
}

type OnboardingMode = "initialize" | "register";

export function WorkspaceOnboarding({ onReady, onError }: WorkspaceOnboardingProps): React.JSX.Element {
  const [mode, setMode] = useState<OnboardingMode>("initialize");
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [repositories, setRepositories] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(): Promise<void> {
    const normalizedPath = path.trim();
    if (!normalizedPath) {
      onError("请先输入 Workspace 路径。");
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
        if (!created) throw new Error("Workspace 已初始化，但未能重新加载注册信息。");
        onReady(created);
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : "Workspace 操作失败。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="onboarding-wrap">
      <section className="onboarding-card">
        <div className="onboarding-symbol"><Sparkles size={23} /></div>
        <p className="eyebrow">Lumon Dashboard</p>
        <h1>先连接一个 Workspace</h1>
        <p className="onboarding-copy">Dashboard 会把 Workspace 列表和配置保存在当前用户的 Lumon 目录中。</p>

        <div className="segmented-control" role="tablist" aria-label="Workspace 操作">
          <button className={mode === "initialize" ? "active" : ""} type="button" onClick={() => setMode("initialize")}>
            <FolderPlus size={16} />初始化新的
          </button>
          <button className={mode === "register" ? "active" : ""} type="button" onClick={() => setMode("register")}>
            <Plus size={16} />添加已有的
          </button>
        </div>

        <label className="field-label" htmlFor="workspace-path">Workspace 路径</label>
        <input id="workspace-path" className="text-input" value={path} onChange={(event) => setPath(event.target.value)} placeholder="例如：/Users/me/Projects/my-workspace" />

        {mode === "initialize" && (
          <>
            <label className="field-label" htmlFor="workspace-name">名称（可选）</label>
            <input id="workspace-name" className="text-input" value={name} onChange={(event) => setName(event.target.value)} placeholder="默认使用目录名称" />
            <label className="field-label" htmlFor="workspace-repositories">Repository URL（可选，每行一个）</label>
            <textarea id="workspace-repositories" className="text-input text-area" value={repositories} onChange={(event) => setRepositories(event.target.value)} placeholder="git@github.com:org/product.git" rows={3} />
            <p className="field-help"><GitBranch size={14} />私有仓库认证继续使用系统 Git、SSH Agent 或 credential helper。</p>
          </>
        )}

        <button className="button button-primary button-wide" type="button" onClick={() => void submit()} disabled={submitting}>
          {submitting ? <LoaderCircle size={17} className="spin" /> : mode === "initialize" ? <FolderPlus size={17} /> : <Plus size={17} />}
          {submitting ? "处理中…" : mode === "initialize" ? "初始化 Workspace" : "添加 Workspace"}
        </button>
      </section>
    </main>
  );
}
