import { act, createElement } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import { I18nProvider, LanguagePicker, translate } from "./i18n";

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

  it("persists the selected language and restores it on the next mount", async () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    window.localStorage.setItem("lumon.locale", "zh-TW");

    try {
      await act(async () => {
        root.render(
          createElement(I18nProvider, null, createElement(LanguagePicker)),
        );
      });

      const picker = container.querySelector("select");
      expect(picker?.value).toBe("zh-TW");

      await act(async () => {
        if (!picker) throw new Error("Language picker was not rendered.");
        picker.value = "en";
        picker.dispatchEvent(new Event("change", { bubbles: true }));
      });

      expect(window.localStorage.getItem("lumon.locale")).toBe("en");
    } finally {
      root.unmount();
      window.localStorage.removeItem("lumon.locale");
    }
  });
});
