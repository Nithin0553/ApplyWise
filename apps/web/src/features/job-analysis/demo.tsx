/** F04 scripted sample posting used to exercise the page without a live call. */
import React from "react";
import ReactDOM from "react-dom/client";
import { JobAnalysisPage } from "./JobAnalysisPage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><JobAnalysisPage /></React.StrictMode>,
);
