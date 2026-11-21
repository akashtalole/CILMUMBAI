import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type ReviewRun } from "../api";
import { forgetToken, readToken, saveToken } from "../token";

// The reviewer's screen is an internal tool and is in English. It shows what is staged, what is held, and takes the
// decision. Nothing here publishes except by answering a gate, and every decision needs a reason (SPEC-021).

const short = (key: string) => key.split("/").slice(2).join("/") || key;

function FileView({ token, fileKey }: { token: string; fileKey: string }) {
  const [text, setText] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  return (
    <li>
      <details
        onToggle={(e) => {
          const now = (e.target as HTMLDetailsElement).open;
          setOpen(now);
          if (now && text === null) api.reviewFile(token, fileKey).then((f) => setText(f.text + (f.truncated ? "\n\n[shortened]" : ""))).catch(() => setText("Could not read this file."));
        }}
      >
        <summary>{short(fileKey)}</summary>
        {open && <pre className="file">{text ?? "Loading…"}</pre>}
      </details>
    </li>
  );
}

function Run({ run, token, onDone }: { run: ReviewRun; token: string; onDone: () => void }) {
  const gate = run.waiting;
  const [picked, setPicked] = useState<string[]>([]);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const decide = async (decision: string | string[]) => {
    setBusy(true);
    setError("");
    try {
      await api.decide(token, run.thread, decision, reason.trim());
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };
  const wards = gate?.wards ?? [];
  const toggle = (ward: string) => setPicked((p) => (p.includes(ward) ? p.filter((w) => w !== ward) : [...p, ward]));

  return (
    <article className="card run">
      <div className="run-head">
        <h3 className="ct">{run.thread}</h3>
        <span className={gate ? "pill-o" : "pill-g"}>{gate ? (gate.gate === "release" ? "Waiting to release" : "Waiting for review") : run.finished ? "Finished" : "Stopped"}</span>
      </div>
      <ul className="runlog">
        {run.log.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>

      {gate && (
        <>
          <p className="lead">{gate.question}</p>
          {gate.gate === "review_facts" && (
            <p className="meta">
              {gate.loaded} facts loaded, {String(gate.held)} held.
            </p>
          )}
          {gate.gate === "release" &&
            wards.map((ward) => {
              const held = (typeof gate.held === "object" && gate.held?.[ward]) || {};
              return (
                <fieldset key={ward} className="ward">
                  <label className="check">
                    <input type="checkbox" checked={picked.includes(ward)} onChange={() => toggle(ward)} />
                    <strong>Release ward {ward}</strong>
                  </label>
                  <p className="meta">Will be published if released</p>
                  <ul className="files">
                    {(gate.staged?.[ward] ?? []).map((k) => (
                      <FileView key={k} token={token} fileKey={k} />
                    ))}
                  </ul>
                  {Object.keys(held).length > 0 && (
                    <>
                      <p className="meta">Held back, whatever you decide</p>
                      <ul className="files held">
                        {Object.entries(held).map(([k, why]) => (
                          <li key={k}>
                            <span>{short(k)}</span> <span className="meta">· {why}</span>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </fieldset>
              );
            })}

          <label className="field-label" htmlFor={`reason-${run.thread}`}>
            Reason (required, kept with your decision)
          </label>
          <textarea id={`reason-${run.thread}`} rows={2} value={reason} maxLength={1000} onChange={(e) => setReason(e.target.value)} />
          <div className="actions">
            {gate.gate === "release" ? (
              <>
                <button type="button" className="primary" disabled={busy || !reason.trim() || picked.length === 0} onClick={() => decide(picked.length === wards.length ? "approve" : picked)}>
                  {picked.length === wards.length ? "Release all wards" : `Release ${picked.length} of ${wards.length}`}
                </button>
                <button type="button" className="secondary" disabled={busy || !reason.trim()} onClick={() => decide("hold")}>
                  Hold everything
                </button>
              </>
            ) : (
              <>
                <button type="button" className="primary" disabled={busy || !reason.trim()} onClick={() => decide("continue")}>
                  Continue to the audit
                </button>
                <button type="button" className="secondary" disabled={busy || !reason.trim()} onClick={() => decide("stop")}>
                  Stop here
                </button>
              </>
            )}
          </div>
          {error && <p className="notice error">{error}</p>}
        </>
      )}

      {run.finished && run.published.length > 0 && <p className="meta">Published {run.published.length} files.</p>}
      {run.decisions.length > 0 && (
        <details className="history">
          <summary>Decisions so far ({run.decisions.length})</summary>
          <ul>
            {run.decisions.map((d, i) => (
              <li key={i}>
                <strong>{d.gate}</strong>: {Array.isArray(d.decision) ? d.decision.join(", ") : d.decision} by {d.account_id} on {d.decided_at.slice(0, 16).replace("T", " ")}. “{d.reason}”
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}

export function Review() {
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
  const [runs, setRuns] = useState<ReviewRun[] | null>(null);
  const [message, setMessage] = useState("");

  const forget = () => {
    forgetToken();
    setToken("");
    setRuns(null);
  };
  const load = useCallback(async () => {
    if (!token) return;
    try {
      setRuns(await api.reviewRuns(token));
      setMessage("");
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setMessage(status === 403 ? "This code is not a reviewer’s." : status === 503 ? "The review screen is not switched on for this server." : "Could not load the runs.");
      if (status === 403) forget();
    }
  }, [token]);
  useEffect(() => {
    load();
  }, [load]);

  if (!token)
    return (
      <section>
        <h2 className="section-title">Review and release</h2>
        <p className="hint">For reviewers. Nothing is published until a reviewer releases it here.</p>
        <form
          className="card"
          onSubmit={(e) => {
            e.preventDefault();
            saveToken(draft.trim());
            setToken(draft.trim());
          }}
        >
          <label htmlFor="review-code" className="field-label">
            Reviewer access code
          </label>
          <div className="search-row">
            <input id="review-code" type="search" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)} />
            <button type="submit" className="primary" disabled={draft.trim().length < 10}>
              OK
            </button>
          </div>
        </form>
        {message && <p className="notice error">{message}</p>}
      </section>
    );

  const waiting = runs?.filter((r) => r.waiting).length ?? 0;
  return (
    <section>
      <h2 className="section-title">Review and release</h2>
      <p className="hint">{runs ? `${waiting} waiting for a decision.` : "Loading…"} Held cases are never published, whatever you decide.</p>
      {message && <p className="notice error">{message}</p>}
      {runs?.length === 0 && <p className="notice">No runs yet.</p>}
      {runs?.map((run) => (
        <Run key={run.thread} run={run} token={token} onDone={load} />
      ))}
      <button type="button" className="linkish" onClick={forget}>
        Forget this code
      </button>
    </section>
  );
}
