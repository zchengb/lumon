import type { SettingsUpdate } from "../../shared/types";

export interface WebhookDraft {
  enabled: boolean;
  url: string;
  clearSavedUrl: boolean;
}

export function buildSettingsUpdate(draft: WebhookDraft): SettingsUpdate {
  const payload: SettingsUpdate = {
    feishu_webhook: {
      enabled: draft.enabled,
    },
  };
  if (draft.clearSavedUrl || draft.url.trim()) {
    payload.feishu_webhook.url = draft.clearSavedUrl ? "" : draft.url.trim();
  }
  return payload;
}
