import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MarkdownPreview } from "./MarkdownPreview";

describe("MarkdownPreview", () => {
  it("renders flow Markdown and keeps frontmatter available", () => {
    const markup = renderToStaticMarkup(
      <MarkdownPreview
        content={'---\nid = "demo"\n---\n# Heading\n\n| Name | Value |\n| --- | --- |\n| A | B |'}
        metadataLabel="Flow metadata"
      />,
    );

    expect(markup).toContain("<summary>Flow metadata</summary>");
    expect(markup).toContain("<h1>Heading</h1>");
    expect(markup).toContain("<table>");
    expect(markup).toContain("<td>B</td>");
  });
});
