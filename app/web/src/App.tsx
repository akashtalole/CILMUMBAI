import { useState } from "react";
import { Alerts } from "./components/Alerts";
import { Ask } from "./components/Ask";
import { MapView } from "./components/MapView";
import { MoneyTrail } from "./components/MoneyTrail";
import { PlaceSearch, type Chosen } from "./components/PlaceSearch";
import { Responsible } from "./components/Responsible";
import { Review } from "./components/Review";
import { LANG_NAMES, type Lang } from "./i18n";
import { useLang } from "./lang";
import { readToken, tierOf } from "./token";

type Tab = "responsible" | "money" | "ask" | "alerts" | "review";
const NOTICE = import.meta.env.VITE_DATA_NOTICE as string | undefined;

export function App() {
  const { t, lang, setLang } = useLang();
  const [tab, setTab] = useState<Tab>("responsible");
  const [place, setPlace] = useState<Chosen | null>(null);
  // The review tab is for reviewers: it shows for a reviewer's access code, or a link ending in #review.
  const [reviewer] = useState(() => tierOf(readToken()) === "reviewer" || window.location.hash.includes("review"));
  const tabs: [Tab, string][] = [
    ["responsible", t.tabResponsible],
    ["money", t.tabMoney],
    ["ask", t.tabAsk],
    ["alerts", t.tabAlerts],
    ...(reviewer ? ([["review", t.tabReview]] as [Tab, string][]) : []),
  ];
  const wide = tab === "responsible" || tab === "money";

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <img src="/favicon.svg" alt="" width="32" height="32" />
          <div>
            <h1>आमचा हिशोब · Aamcha Hishob</h1>
            <p>{t.tagline}</p>
          </div>
        </div>
        <div className="langs" role="group" aria-label="Language">
          {(Object.keys(LANG_NAMES) as Lang[]).map((l) => (
            <button key={l} type="button" className={l === lang ? "on" : ""} aria-pressed={l === lang} onClick={() => setLang(l)}>
              {LANG_NAMES[l]}
            </button>
          ))}
        </div>
      </header>
      {NOTICE && <div className="demo-banner">{NOTICE}</div>}

      <nav className="tabs" role="tablist">
        {tabs.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      <main className={`layout ${wide ? "" : "single"}`}>
        {wide && (
          <div className="pane">
            <PlaceSearch chosen={place} onChoose={setPlace} />
            {place && (
              <p className="chosen">
                {place.name}
                {place.ward && <span className="meta"> · {t.ward} {place.ward}</span>}
              </p>
            )}
            {tab === "responsible" ? <Responsible placeId={place?.id ?? null} /> : <MoneyTrail placeId={place?.id ?? null} />}
          </div>
        )}
        {wide && (
          <div className="pane map-pane">
            <MapView placeId={place?.id ?? null} />
          </div>
        )}
        {tab === "ask" && (
          <div className="pane">
            <Ask />
          </div>
        )}
        {tab === "alerts" && (
          <div className="pane">
            <Alerts place={place} />
          </div>
        )}
        {tab === "review" && (
          <div className="pane">
            <Review />
          </div>
        )}
      </main>
      <footer className="foot">{t.footer}</footer>
    </div>
  );
}
