import { describe, expect, it } from "vitest";
import { readNavigation, writeNavigation } from "./navigation";

describe("Dashboard navigation", () => {
  it("reads a Workspace and supported view from the URL", () => {
    expect(readNavigation("?workspace=abc&view=settings")).toEqual({
      workspaceId: "abc",
      view: "settings",
    });
  });

  it("falls back to overview for an unknown view", () => {
    expect(readNavigation("?workspace=abc&view=scan")).toEqual({
      workspaceId: "abc",
      view: "overview",
    });
  });

  it("keeps the Agent settings view in the URL", () => {
    expect(readNavigation("?workspace=abc&view=agent")).toEqual({
      workspaceId: "abc",
      view: "agent",
    });
    expect(writeNavigation({ workspaceId: "abc", view: "agent" })).toBe(
      "?workspace=abc&view=agent",
    );
  });

  it("keeps the Flows view in the URL", () => {
    expect(readNavigation("?workspace=abc&view=flows")).toEqual({
      workspaceId: "abc",
      view: "flows",
    });
    expect(writeNavigation({ workspaceId: "abc", view: "flows" })).toBe(
      "?workspace=abc&view=flows",
    );
  });

  it("keeps the Capabilities view in the URL", () => {
    expect(readNavigation("?workspace=abc&view=capabilities")).toEqual({
      workspaceId: "abc",
      view: "capabilities",
    });
    expect(writeNavigation({ workspaceId: "abc", view: "capabilities" })).toBe(
      "?workspace=abc&view=capabilities",
    );
  });

  it("writes stable query state", () => {
    expect(writeNavigation({ workspaceId: "abc", view: "settings" })).toBe(
      "?workspace=abc&view=settings",
    );
  });
});
