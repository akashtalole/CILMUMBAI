import type { ReactNode } from "react";

const BULLET = /^\s*[-*•]\s+/;

/** The desk writes light Markdown: paragraphs, "- " bullets and **bold**. Rendered as React elements, never as
 * HTML, so nothing in a reply can inject markup. */
export function Rich({ text }: { text: string }) {
  const out: ReactNode[] = [];
  for (const [i, block] of text.trim().split(/\n{2,}/).entries()) {
    let lines: string[] = [];
    let items: string[] = [];
    const flush = (key: string) => {
      if (lines.length) out.push(<p key={`p${key}`}>{lines.flatMap((l, j) => (j ? [<br key={j} />, ...inline(l)] : inline(l)))}</p>);
      if (items.length) out.push(<ul key={`u${key}`}>{items.map((l, j) => <li key={j}>{inline(l)}</li>)}</ul>);
      lines = [];
      items = [];
    };
    block.split("\n").forEach((line, j) => {
      if (BULLET.test(line)) {
        if (lines.length) flush(`${i}-${j}`);
        items.push(line.replace(BULLET, ""));
      } else if (line.trim()) {
        if (items.length) flush(`${i}-${j}`);
        lines.push(line);
      }
    });
    flush(`${i}-end`);
  }
  return <div className="rich">{out}</div>;
}

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4 ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  );
}
