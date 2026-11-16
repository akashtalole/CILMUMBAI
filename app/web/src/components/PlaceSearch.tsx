import { useEffect, useRef, useState } from "react";
import { api, type Place } from "../api";
import { useLang } from "../lang";

export interface Chosen {
  id: string;
  name: string;
  kind: string;
  ward?: string;
}

/** Find a road or ward by name (either script), or from the phone's location. */
export function PlaceSearch({ chosen, onChoose }: { chosen: Chosen | null; onChoose: (c: Chosen) => void }) {
  const { t } = useLang();
  const [text, setText] = useState(chosen?.name ?? "");
  const [results, setResults] = useState<Place[] | null>(null);
  const [status, setStatus] = useState<string>("");
  const timer = useRef<number>();

  useEffect(() => setText(chosen?.name ?? ""), [chosen?.id]);

  const search = (value: string) => {
    setText(value);
    window.clearTimeout(timer.current);
    if (value.trim().length < 2) return setResults(null);
    timer.current = window.setTimeout(() => {
      api.places(value.trim()).then(setResults).catch(() => setResults([]));
    }, 250);
  };

  const pick = (p: Place) => {
    setResults(null);
    onChoose({ id: p.node_id, name: p.name, kind: p.kind });
  };

  const nearMe = () => {
    if (!navigator.geolocation) return setStatus(t.noLocation);
    setStatus(t.locating);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const here = await api.point(coords.latitude, coords.longitude);
          setStatus("");
          if (here.road) onChoose({ id: here.road.node_id, name: here.road.name, kind: "Road", ward: here.admin_ward?.code });
          else if (here.admin_ward) onChoose({ id: here.admin_ward.node_id, name: here.admin_ward.code, kind: "AdminWard" });
          else setStatus(t.noMatch);
        } catch {
          setStatus(t.noLocation);
        }
      },
      () => setStatus(t.noLocation),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  return (
    <div className="search">
      <label htmlFor="place" className="field-label">
        {t.searchLabel}
      </label>
      <div className="search-row">
        <input
          id="place"
          type="search"
          autoComplete="off"
          value={text}
          placeholder={t.searchPlaceholder}
          onChange={(e) => search(e.target.value)}
          aria-autocomplete="list"
          aria-controls="place-results"
        />
        <button type="button" className="secondary" onClick={nearMe}>
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
            <path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" fill="currentColor" />
          </svg>
          {t.nearMe}
        </button>
      </div>
      {results && (
        <ul id="place-results" className="results" role="listbox">
          {results.length === 0 && <li className="empty">{t.noMatch}</li>}
          {results.map((p) => (
            <li key={p.node_id}>
              <button type="button" role="option" aria-selected={false} onClick={() => pick(p)}>
                <span>{p.name}</span>
                <span className="kind">{p.kind === "Road" ? "🛣" : t.ward}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {status && <p className="hint">{status}</p>}
    </div>
  );
}
