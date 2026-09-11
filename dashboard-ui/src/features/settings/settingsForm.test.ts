import { describe, expect, it } from "vitest";
import { buildSettingsUpdate } from "./settingsForm";

describe("Webhook settings form", () => {
  it("omits an untouched URL so the saved secret is retained", () => {
    expect(buildSettingsUpdate({ enabled: true, url: "" })).toEqual({
      feishu_webhook: { enabled: true },
    });
  });

  it("trims a replacement URL", () => {
    expect(buildSettingsUpdate({ enabled: true, url: "  https://example.test/hook  " })).toEqual({
      feishu_webhook: { enabled: true, url: "https://example.test/hook" },
    });
  });
});
