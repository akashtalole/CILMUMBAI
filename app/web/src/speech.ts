import { useCallback, useEffect, useRef, useState } from "react";
import type { Lang } from "./i18n";

// Speech to text with the browser's own recogniser (SPEC-020/R10). It is as good as the browser makes it, differs
// between browsers, and in some the audio goes to the browser maker's speech service, which the page says. It fills
// the question box and never sends: the words are the resident's to check, because a place name heard wrongly would
// send them to the wrong road.

const LOCALES: Record<Lang, string> = { mr: "mr-IN", hi: "hi-IN", en: "en-IN" };

interface Recogniser {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((e: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

const ctor = (): (new () => Recogniser) | null => {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as (new () => Recogniser) | null;
};

export type SpeechProblem = "denied" | "nospeech" | "unsupported" | "failed";

export function useSpeech(lang: Lang, onText: (text: string) => void) {
  const supported = ctor() !== null;
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [problem, setProblem] = useState<SpeechProblem | null>(null);
  const active = useRef<Recogniser | null>(null);
  const deliver = useRef(onText);
  deliver.current = onText;

  useEffect(() => () => active.current?.abort(), []);

  const start = useCallback(() => {
    const Recognition = ctor();
    if (!Recognition) return setProblem("unsupported");
    setProblem(null);
    setInterim("");
    const r = new Recognition();
    r.lang = LOCALES[lang];
    r.interimResults = true;
    r.continuous = false;
    r.maxAlternatives = 1;
    r.onresult = (e) => {
      let live = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const piece = e.results[i][0].transcript;
        if (e.results[i].isFinal) deliver.current(piece.trim());
        else live += piece;
      }
      setInterim(live);
    };
    r.onerror = (e) =>
      setProblem(e.error === "not-allowed" || e.error === "service-not-allowed" ? "denied" : e.error === "no-speech" ? "nospeech" : e.error === "aborted" ? null : "failed");
    r.onend = () => {
      setListening(false);
      setInterim("");
      active.current = null;
    };
    active.current = r;
    setListening(true);
    try {
      r.start();
    } catch {
      setListening(false);
      setProblem("failed");
    }
  }, [lang]);

  const stop = useCallback(() => active.current?.stop(), []);
  return { supported, listening, interim, problem, start, stop };
}
