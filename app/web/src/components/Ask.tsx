import { useEffect, useRef, useState } from "react";
import { ApiError, api, type Answer } from "../api";
import { useLang } from "../lang";
import { useSpeech } from "../speech";
import { AnswerCard } from "./AnswerCard";
import { PhotoReport } from "./PhotoReport";

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
  const poll = useRef<number>();
  const voice = useSpeech(lang, (heard) => setQuestion((q) => (q.trim() ? `${q.trim()} ${heard}` : heard)));

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
        {voice.supported && (
          <div className="voice">
            <button
              type="button"
              className={`secondary mic ${voice.listening ? "on" : ""}`}
              aria-pressed={voice.listening}
              onClick={voice.listening ? voice.stop : voice.start}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1A7 7 0 0 0 19 11z" fill="currentColor" />
              </svg>
              {voice.listening ? t.voiceStop : t.voiceStart}
            </button>
            <span className="meta" role="status">
              {voice.listening ? (voice.interim || t.voiceListening) : voice.problem === "denied" ? t.voiceDenied : voice.problem === "nospeech" ? t.voiceNoSpeech : voice.problem ? t.voiceFailed : ""}
            </span>
          </div>
        )}
        {voice.supported && <p className="hint small">{t.voiceNote}</p>}
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

      {answer && <AnswerCard answer={answer} />}

      <PhotoReport />
    </section>
  );
}
