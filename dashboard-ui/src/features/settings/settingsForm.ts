import type { SettingsUpdate } from "../../shared/types";

export interface WebhookDraft {
  enabled: boolean;
  url: string;
}

export function buildSettingsUpdate(draft: WebhookDraft): SettingsUpdate {
  const payload: SettingsUpdate = {
    feishu_webhook: {
      enabled: draft.enabled,
    },
  };
  if (draft.url.trim()) {
    payload.feishu_webhook.url = draft.url.trim();
  }
  return payload;
}
