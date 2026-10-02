import { useState } from "react";
import { ResumePreview } from "./ResumePreview";
import "./ResumePage.css";

export function ResumePage() {
  const [template, setTemplate] = useState("standard");

  return (
    <section className="resume-workspace" aria-labelledby="resume-heading">
      <header className="workspace-heading">
        <p className="workspace-eyebrow">RESUME STUDIO</p>
        <h2 id="resume-heading">Build your resume</h2>
        <p>Choose a clear layout for your approved experience.</p>
      </header>

      <p className="prototype-notice">
        Prototype · Fictional sample content representing approved statements.
        Verification and export are not connected.
      </p>

      <div className="resume-layout">
        <aside className="resume-controls" aria-labelledby="settings-heading">
          <h3 id="settings-heading">Document settings</h3>

          <label htmlFor="resume-template">Resume template</label>
          <select
            id="resume-template"
            value={template}
            onChange={(event) => setTemplate(event.target.value)}
          >
            <option value="standard">Standard</option>
            <option value="compact">Compact</option>
          </select>

          <p className="template-description">
            {template === "standard"
              ? "Comfortable spacing with clear section headings."
              : "Tighter spacing for a more condensed presentation."}
          </p>

          <p>
            Selected template: {template === "standard" ? "Standard" : "Compact"}
          </p>

          <hr />

          <h3>Export your resume</h3>
          <p id="export-note">
            PDF and Word downloads will be available when export is implemented.
          </p>

          <div className="export-actions">
            <button type="button" disabled aria-describedby="export-note">
              Download PDF
            </button>
            <button type="button" disabled aria-describedby="export-note">
              Download Word
            </button>
          </div>
        </aside>

        <section className="preview-area" aria-labelledby="preview-heading">
          <div className="preview-heading">
            <h3 id="preview-heading">Resume preview</h3>
            <span>Sample content</span>
          </div>

          <ResumePreview template={template} />
        </section>
      </div>
    </section>
  );
}