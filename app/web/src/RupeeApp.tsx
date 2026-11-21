import { Rupee } from "./components/Rupee";
import { LANG_NAMES, type Lang } from "./i18n";
import { useLang } from "./lang";

// Follow the Rupee on its own (VITE_RUPEE_ONLY=1): one tool, nothing else, for the Impact Lab demo.
export function RupeeApp() {
  const { lang, setLang } = useLang();
  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <img src="favicon.svg" alt="" width="32" height="32" />
          <div>
            <h1>Follow the Rupee · रुपयाचा माग</h1>
            <p>Where each ward's monsoon road money went, whether the fix held, and where the next rupee should go</p>
          </div>
        </div>
        <div className="langs" role="group" aria-label="Language for complaint answers">
          {(Object.keys(LANG_NAMES) as Lang[]).map((l) => (
            <button key={l} type="button" className={l === lang ? "on" : ""} aria-pressed={l === lang} onClick={() => setLang(l)}>
              {LANG_NAMES[l]}
            </button>
          ))}
        </div>
      </header>
      <main className="layout full">
        <div className="pane">
          <Rupee />
        </div>
      </main>
      <footer className="foot">
        Records, not verdicts: every figure links to the dataset row it came from. Built with Claude for Claude Impact Lab Mumbai on synthetic data. Not an official BMC service.
      </footer>
    </div>
  );
}
