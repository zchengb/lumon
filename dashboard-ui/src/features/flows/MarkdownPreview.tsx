import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownPreviewProps {
  content: string;
  metadataLabel: string;
}

export function MarkdownPreview({ content, metadataLabel }: MarkdownPreviewProps): React.JSX.Element {
  const { frontmatter, body } = splitFrontmatter(content);

  return (
    <div className="flow-markdown-preview" aria-label={metadataLabel}>
      {frontmatter && (
        <details className="flow-markdown-frontmatter" open>
          <summary>{metadataLabel}</summary>
          <pre>{`---\n${frontmatter}\n---`}</pre>
        </details>
      )}
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
    </div>
  );
}

function splitFrontmatter(content: string): { frontmatter: string | null; body: string } {
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(content);
  if (!match) return { frontmatter: null, body: content };
  return { frontmatter: match[1], body: content.slice(match[0].length) };
}
