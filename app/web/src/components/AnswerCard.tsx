import { useState } from "react";
import type { Answer } from "../api";
import { useLang } from "../lang";
import { Rich } from "./Rich";

/** A desk's answer: the text, each source passage once, and a letter to copy, share on WhatsApp or download. */
export function AnswerCard({ answer }: { answer: Answer }) {
  const { t } = useLang();
  const [copied, setCopied] = useState(false);

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  const download = (text: string) => {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    link.download = "letter.txt";
    link.click();
    URL.revokeObjectURL(link.href);
  };

  return (
    <article className="card answer" aria-live="polite">
      {answer.status === "fallback" && <p className="notice">{t.fallbackNote}</p>}
      <Rich text={answer.body} />
      {answer.sources.length > 0 && (
        <details className="answer-sources" open>
          <summary>{t.answerSources}</summary>
          <ul>
            {unique(answer.sources).map((s) => (
              <li key={s.fact_id}>
                <q>{s.quote}</q>
                <span className="meta">{t.sourceOf(s.publisher || "?", s.page)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
      {answer.draft_letter && (
        <div className="letter">
          <h4>{t.letter}</h4>
          <pre>{answer.draft_letter}</pre>
          <div className="actions">
            <button type="button" className="secondary" onClick={() => copy(answer.draft_letter!)}>
              {copied ? t.copied : t.copy}
            </button>
            <a className="button whatsapp" href={`https://wa.me/?text=${encodeURIComponent(answer.draft_letter)}`} target="_blank" rel="noreferrer">
              {t.share}
            </a>
            <button type="button" className="secondary" onClick={() => download(answer.draft_letter!)}>
              {t.download}
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

/** Several facts often cite the same line of the same page; show each passage once. */
function unique(sources: Answer["sources"]): Answer["sources"] {
  const seen = new Set<string>();
  return sources.filter((s) => {
    const key = `${s.document}|${s.page}|${s.quote}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
