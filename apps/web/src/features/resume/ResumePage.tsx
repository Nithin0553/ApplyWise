import { useState } from "react";

export function ResumePage() {
  const [template, setTemplate] = useState("standard");

  return (
    <section aria-labelledby="resume-heading">
      <h2 id="resume-heading">Build your resume</h2>
      <p>Choose a resume template and export your approved content.</p>

      <label htmlFor="resume-template">Resume template</label>{" "}
      <select
        id="resume-template"
        value={template}
        onChange={(event) => setTemplate(event.target.value)}
      >
        <option value="standard">Standard</option>
        <option value="compact">Compact</option>
      </select>

      <p>
        Selected template: {template === "standard" ? "Standard" : "Compact"}
      </p>
      <p>Prototype: template layouts and document export are not available yet.</p>
    </section>
  );
}