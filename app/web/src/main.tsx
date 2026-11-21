import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { RupeeApp } from "./RupeeApp";
import { LangProvider } from "./lang";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LangProvider>
      {import.meta.env.VITE_RUPEE_ONLY === "1" ? <RupeeApp /> : <App />}
    </LangProvider>
  </StrictMode>,
);
