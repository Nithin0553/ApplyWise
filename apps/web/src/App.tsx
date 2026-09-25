import { ResumePage } from "./features/resume/ResumePage";
import "./App.css";

export function App() {
  return (
    <div className="applywise-app">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <header className="app-header">
        <div className="app-header-inner">
          <h1>ApplyWise</h1>
          <span className="app-badge">Design prototype</span>
        </div>
      </header>

      <main id="main-content" className="app-main" tabIndex={-1}>
        <ResumePage />
      </main>
    </div>
  );
}