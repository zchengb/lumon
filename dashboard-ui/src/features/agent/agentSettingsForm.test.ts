import { describe, expect, it } from "vitest";
import { buildAgentSettingsUpdate, type AgentSettingsDraft } from "./agentSettingsForm";

const draft: AgentSettingsDraft = {
  enabled: true,
  defaultWorkspaceId: "workspace-1",
  agentModel: "  gpt-5.6-luna  ",
  agentReasoningEffort: "max",
  feishuAppId: "  cli_test  ",
  feishuAppSecret: "",
  langfuseEnabled: true,
  langfuseBaseUrl: "  https://cloud.langfuse.com  ",
  langfuseSampleRate: "0.25",
  langfusePublicKey: "",
  langfuseSecretKey: "",
  clearLangfuseCredentials: false,
};

describe("Agent settings form", () => {
  it("trims editable values and preserves untouched secrets", () => {
    expect(buildAgentSettingsUpdate(draft)).toEqual({
      enabled: true,
      default_workspace_id: "workspace-1",
      agent_model: "gpt-5.6-luna",
      agent_reasoning_effort: "max",
      feishu_app_id: "cli_test",
      observability: {
        enabled: true,
        base_url: "https://cloud.langfuse.com",
        sample_rate: 0.25,
        clear_credentials: false,
      },
    });
  });

  it("includes replacement and clear flags for secrets", () => {
    expect(buildAgentSettingsUpdate({
      ...draft,
      feishuAppSecret: "feishu-secret",
      langfusePublicKey: "pk-lf-public",
      langfuseSecretKey: "sk-lf-secret",
      clearLangfuseCredentials: true,
    })).toMatchObject({
      feishu_app_secret: "feishu-secret",
      observability: {
        public_key: "pk-lf-public",
        secret_key: "sk-lf-secret",
        clear_credentials: true,
      },
    });
  });
});
