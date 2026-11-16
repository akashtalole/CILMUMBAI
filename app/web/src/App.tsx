import { useState } from "react";
import { Ask } from "./components/Ask";
import { MapView } from "./components/MapView";
import { MoneyTrail } from "./components/MoneyTrail";
import { PlaceSearch, type Chosen } from "./components/PlaceSearch";
import { Responsible } from "./components/Responsible";
import { LANG_NAMES, type Lang } from "./i18n";
import { useLang } from "./lang";

type Tab = "responsible" | "money" | "ask";
const NOTICE = import.meta.env.VITE_DATA_NOTICE as string | undefined;

export function App() {
  const { t, lang, setLang } = useLang();
  const [tab, setTab] = useState<Tab>("responsible");
  const [place, setPlace] = useState<Chosen | null>(null);
  const tabs: [Tab, string][] = [
    ["responsible", t.tabResponsible],
    ["money", t.tabMoney],
    ["ask", t.tabAsk],
  ];

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

      <main className={`layout ${tab === "ask" ? "single" : ""}`}>
        {tab !== "ask" && (
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
        {tab !== "ask" && (
          <div className="pane map-pane">
            <MapView placeId={place?.id ?? null} />
          </div>
        )}
        {tab === "ask" && (
          <div className="pane">
            <Ask />
          </div>
        )}
      </main>
      <footer className="foot">{t.footer}</footer>
    </div>
  );
}
