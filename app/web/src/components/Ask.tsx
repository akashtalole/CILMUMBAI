import { useEffect, useRef, useState } from "react";
import { ApiError, api, type Answer } from "../api";
import { useLang } from "../lang";
import { Rich } from "./Rich";

/** Ask the citizen desk in any of three languages. The answer comes back with its sources and, when useful,
 * a letter the resident can copy, share or download. */
export function Ask() {
  const { t, lang } = useLang();
  const [question, setQuestion] = useState("");
  const [useLocation, setUseLocation] = useState(false);
  const [state, setState] = useState<"idle" | "asking" | "done" | "error">("idle");
  const [elapsed, setElapsed] = useState(0);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState(false);
  const poll = useRef<number>();

  useEffect(() => () => window.clearTimeout(poll.current), []);

  const location = () =>
    new Promise<{ lat: number; lon: number } | undefined>((resolve) => {
      if (!useLocation || !navigator.geolocation) return resolve(undefined);
      navigator.geolocation.getCurrentPosition(
        ({ coords }) => resolve({ lat: coords.latitude, lon: coords.longitude }),
        () => resolve(undefined),
        { timeout: 8000 },
      );
    });

  const send = async (text = question) => {
    if (text.trim().length < 3 || state === "asking") return;
    setQuestion(text);
    setState("asking");
    setAnswer(null);
    setElapsed(0);
    try {
      const { id } = await api.ask(text.trim(), lang, await location());
      const check = async () => {
        const job = await api.askStatus(id);
        setElapsed(job.elapsed_s);
        if (job.status === "running") poll.current = window.setTimeout(check, 2000);
        else if (job.status === "done" && job.answer) {
          setAnswer(job.answer);
          setState("done");
        } else {
          setMessage(t.askFailed);
          setState("error");
        }
      };
      poll.current = window.setTimeout(check, 1500);
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setMessage(status === 503 ? t.askDisabled : status === 429 ? t.askBusy : t.askFailed);
      setState("error");
    }
  };

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
    <section>
      <h2 className="section-title">{t.askTitle}</h2>
      <form
        className="ask"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t.askPlaceholder}
          rows={3}
          maxLength={1000}
          aria-label={t.askPlaceholder}
        />
        <p className="hint small">{t.privacy}</p>
        <div className="ask-row">
          <label className="check">
            <input type="checkbox" checked={useLocation} onChange={(e) => setUseLocation(e.target.checked)} />
            {t.useLocation}
          </label>
          <button type="submit" className="primary" disabled={state === "asking" || question.trim().length < 3}>
            {t.send}
          </button>
        </div>
      </form>

      {state === "idle" && (
        <div className="examples">
          {t.askExamples.map((example) => (
            <button key={example} type="button" className="chip" onClick={() => send(example)}>
              {example}
            </button>
          ))}
        </div>
      )}

      {state === "asking" && (
        <div className="thinking" role="status">
          <span className="spinner" aria-hidden />
          <span>{elapsed > 25 ? t.thinkingLong : t.thinking}</span>
          <span className="meta">{Math.round(elapsed)} s</span>
        </div>
      )}

      {state === "error" && <p className="notice error">{message}</p>}

      {answer && (
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
      )}
    </section>
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
