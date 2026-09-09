import { describe, expect, it } from "vitest";
import { buildSettingsUpdate } from "./settingsForm";

describe("Webhook settings form", () => {
  it("omits an untouched URL so the saved secret is retained", () => {
    expect(buildSettingsUpdate({ enabled: true, url: "", clearSavedUrl: false })).toEqual({
      feishu_webhook: { enabled: true },
    });
  });

  it("uses an empty URL as the explicit clear operation", () => {
    expect(buildSettingsUpdate({ enabled: false, url: "", clearSavedUrl: true })).toEqual({
      feishu_webhook: { enabled: false, url: "" },
    });
  });

  it("trims a replacement URL", () => {
    expect(buildSettingsUpdate({ enabled: true, url: "  https://example.test/hook  ", clearSavedUrl: false })).toEqual({
      feishu_webhook: { enabled: true, url: "https://example.test/hook" },
    });
  });
});
