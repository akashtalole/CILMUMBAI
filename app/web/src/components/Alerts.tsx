import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type Alert, type SavedArea } from "../api";
import { useLang } from "../lang";
import { forgetToken, readToken, saveToken } from "../token";
import type { Chosen } from "./PlaceSearch";

const RADII = [100, 300, 500, 1000];

/** Saved areas and the alerts queued for them (SPEC-010). */
export function Alerts({ place }: { place: Chosen | null }) {
  const { t, lang } = useLang();
  const [token, setToken] = useState(readToken);
  const [draft, setDraft] = useState("");
  const [areas, setAreas] = useState<SavedArea[] | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [radius, setRadius] = useState(300);
  const [message, setMessage] = useState("");

  const forget = () => {
    forgetToken();
    setToken("");
    setAreas(null);
  };

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setAreas(await api.areas(token));
      setAlerts(await api.alerts(token));
      setMessage("");
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        forget();
        setMessage(t.accessBad);
      } else setMessage(t.error);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (area: Record<string, unknown>) => {
    try {
      await api.saveArea(token, { ...area, language: lang });
      await load();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : t.error);
    }
  };
  const saveHere = () => {
    if (!navigator.geolocation) return setMessage(t.noLocation);
    setMessage(t.locating);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => save({ kind: "point", lat: coords.latitude, lon: coords.longitude, radius_m: radius }),
      () => setMessage(t.noLocation),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  if (!token)
    return (
      <section>
        <h2 className="section-title">{t.alertsTitle}</h2>
        <p className="hint">{t.alertsIntro}</p>
        <form
          className="card"
          onSubmit={(e) => {
            e.preventDefault();
            saveToken(draft.trim());
            setToken(draft.trim());
          }}
        >
          <label htmlFor="code" className="field-label">
            {t.accessCode}
          </label>
          <div className="search-row">
            <input id="code" type="search" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)} />
            <button type="submit" className="primary" disabled={draft.trim().length < 10}>
              OK
            </button>
          </div>
          <p className="hint small">{t.accessHelp}</p>
        </form>
        {message && <p className="notice error">{message}</p>}
      </section>
    );

  return (
    <section>
      <h2 className="section-title">{t.alertsTitle}</h2>
      <p className="hint">{t.alertsIntro}</p>
      <div className="card">
        <div className="ask-row">
          <label className="check">
            {t.radius}
            <select value={radius} onChange={(e) => setRadius(Number(e.target.value))}>
              {RADII.map((r) => (
                <option key={r} value={r}>
                  {r} {t.metres}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="primary" onClick={saveHere}>
            {t.saveHere}
          </button>
        </div>
        {place?.kind === "Road" && (
          <button type="button" className="secondary" style={{ marginTop: 10 }} onClick={() => save({ kind: "roads", road_ids: [place.id] })}>
            {t.saveRoad(place.name)}
          </button>
        )}
        {message && <p className="hint small">{message}</p>}
      </div>

      <h3 className="sub-title">{t.savedAreas}</h3>
      {areas && areas.length === 0 && <p className="notice">{t.noAreas}</p>}
      <ul className="plain">
        {areas?.map((a) => (
          <li key={a.id} className="row">
            <span>{a.kind === "point" ? t.areaPoint(a.radius_m ?? 0) : t.areaRoads(a.road_ids.length)}</span>
            <button type="button" className="secondary" onClick={() => api.removeArea(token, a.id).then(load)}>
              {t.remove}
            </button>
          </li>
        ))}
      </ul>

      <h3 className="sub-title">{t.yourAlerts}</h3>
      {alerts.length === 0 && <p className="notice">{t.noAlerts}</p>}
      {alerts.map((a) => {
        const lines = a.text.split("\n");
        const link = lines[lines.length - 1].match(/https?:\/\/\S+|\/sources\/\S+/)?.[0];
        return (
          <article key={a.id} className="card alert">
            <p className="lead">{lines[0]}</p>
            {lines.slice(1, -1).map((line) => (
              <p key={line} className="meta">
                {line}
              </p>
            ))}
            {link && (
              <a href={link} target="_blank" rel="noreferrer">
                {t.openSource}
              </a>
            )}
          </article>
        );
      })}
      <button type="button" className="linkish" onClick={forget}>
        {t.signOut}
      </button>
    </section>
  );
}
