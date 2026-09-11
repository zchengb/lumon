import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { I18nProvider } from "./shared/i18n";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("Lumon Dashboard root element is missing.");

createRoot(root).render(
  <StrictMode>
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>,
);
