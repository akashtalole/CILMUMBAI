import { useEffect, useRef, useState } from "react";
import { ApiError, api, type PhotoResult } from "../api";
import { useLang } from "../lang";
import { AnswerCard } from "./AnswerCard";

const MAX_SIDE = 1568;

/** Shrink a phone photo before it leaves the phone. Drawing it on a canvas also drops its metadata, so the location
 * tag never travels: the page asks the browser for the position instead, and only with the resident's say-so. */
async function shrink(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, "image/jpeg", 0.85));
    if (blob) return blob;
  } catch {
    /* an unusual format: send the file as it is and let the server judge it */
  }
  return file;
}

const here = () =>
  new Promise<{ lat: number; lon: number } | null>((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ lat: coords.latitude, lon: coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  });

/** Report a problem from a photo: what it shows, whose it is, and a letter to send (SPEC-030). */
export function PhotoReport() {
  const { t, lang } = useLang();
  const [state, setState] = useState<"idle" | "working" | "done" | "error">("idle");
  const [preview, setPreview] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<PhotoResult | null>(null);
  const [message, setMessage] = useState("");
  const poll = useRef<number>();
  const picker = useRef<HTMLInputElement>(null);

  useEffect(
    () => () => {
      window.clearTimeout(poll.current);
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  const send = async (file: File) => {
    window.clearTimeout(poll.current);
    setResult(null);
    setMessage("");
    setElapsed(0);
    setState("working");
    setPreview((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(file);
    });
    const where = await here();
    if (!where) {
      setMessage(t.photoNoLocation);
      return setState("error");
    }
    try {
      const { id } = await api.report(await shrink(file), lang, where);
      const check = async () => {
        const job = await api.reportStatus(id);
        setElapsed(job.elapsed_s);
        if (job.status === "running") poll.current = window.setTimeout(check, 2000);
        else if (job.status === "done" && job.answer) {
          setResult(job.answer);
          setState("done");
        } else {
          setMessage(t.askFailed);
          setState("error");
        }
      };
      poll.current = window.setTimeout(check, 1500);
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setMessage(status === 503 ? t.photoDisabled : status === 429 ? t.askBusy : status === 413 || status === 415 || status === 422 ? t.photoBadFile : t.askFailed);
      setState("error");
    }
  };

  return (
    <section className="card photo">
      <h3 className="ct">{t.photoTitle}</h3>
      <p className="hint">{t.photoHelp}</p>
      <input
        ref={picker}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        data-testid="photo-input"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) send(file);
          e.target.value = "";
        }}
      />
      <div className="actions">
        <button type="button" className="primary" disabled={state === "working"} onClick={() => picker.current?.click()}>
          {t.photoChoose}
        </button>
      </div>

      {preview && <img className="photo-preview" src={preview} alt={t.photoAlt} />}

      {state === "working" && (
        <div className="thinking" role="status">
          <span className="spinner" aria-hidden />
          <span>{t.photoWorking}</span>
          <span className="meta">{Math.round(elapsed)} s</span>
        </div>
      )}
      {state === "error" && <p className="notice error">{message}</p>}

      {result && result.status === "no_location" && <p className="notice">{t.photoNoLocation}</p>}
      {result && result.status === "unclear" && <p className="notice">{t.photoUnclear}</p>}
      {result && result.status === "answered" && result.issue && (
        <>
          <p className="saw">
            <span className="meta">{t.photoSaw}</span> <strong>{t.issues[result.issue as keyof typeof t.issues] ?? result.issue}</strong>
          </p>
          {result.answer && <AnswerCard answer={result.answer} />}
        </>
      )}
    </section>
  );
}
