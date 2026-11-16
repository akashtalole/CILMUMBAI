import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { STRINGS, type Lang } from "./i18n";

const LangContext = createContext<{ lang: Lang; t: (typeof STRINGS)["en"]; setLang: (l: Lang) => void }>({
  lang: "mr",
  t: STRINGS.mr,
  setLang: () => undefined,
});

function initial(): Lang {
  try {
    const saved = localStorage.getItem("hishob.lang");
    if (saved === "mr" || saved === "hi" || saved === "en") return saved;
  } catch {
    /* storage may be blocked */
  }
  const browser = navigator.language.slice(0, 2);
  return browser === "hi" ? "hi" : browser === "en" ? "en" : "mr"; // Marathi first: it is Mumbai's language
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initial);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("hishob.lang", l);
    } catch {
      /* ignore */
    }
  };
  return <LangContext.Provider value={{ lang, t: STRINGS[lang], setLang }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
