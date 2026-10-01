import { useState } from "react";

interface Props {
  title: string;
  value: unknown;
  defaultOpen?: boolean;
}

// Collapsible, formatted JSON viewer with a copy button. The value is rendered
// via JSON.stringify (text only) so no model output is interpreted as HTML.
export function JsonViewer({ title, value, defaultOpen = false }: Props) {
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(value, null, 2);

  async function copy(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <details open={defaultOpen}>
      <summary>
        {title}
        <button className="small" style={{ float: "right" }} onClick={copy}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </summary>
      <pre className="json">{text}</pre>
    </details>
  );
}
