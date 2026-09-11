import { describe, expect, it } from "vitest";
import { translate } from "./i18n";

describe("Dashboard translations", () => {
  it("provides the three supported interface languages", () => {
    expect(translate("en", "settings.title")).toBe("Settings");
    expect(translate("zh-CN", "settings.title")).toBe("配置");
    expect(translate("zh-TW", "settings.title")).toBe("設定");
  });

  it("interpolates dynamic values without changing the translation template", () => {
    expect(translate("en", "app.workspaceReady", { name: "Demo" })).toBe(
      "Workspace “Demo” is ready.",
    );
    expect(translate("zh-TW", "overview.createdAt", { date: "2026/09/11" })).toBe(
      "建立於 2026/09/11",
    );
  });
});
