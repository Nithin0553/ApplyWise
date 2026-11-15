import type { ResumeVersionSnapshot } from "../applications/api";
import { buildSections, entryLabel } from "./sections";

type ResumePreviewProps = {
  template: string;
  snapshot?: ResumeVersionSnapshot;
  fullName?: string;
  targetRole?: string;
  company?: string | null;
};

/**
 * The selected saved version, laid out the way F10 renders it. This used to
 * be a fixed fictional resume, which meant the page showed a document the
 * user had never written and could not be checked against the download.
 */
export function ResumePreview({
  template,
  snapshot,
  fullName,
  targetRole,
  company,
}: ResumePreviewProps) {
  if (!snapshot) {
    return (
      <article
        className={`resume-preview resume-preview--${template}`}
        aria-label="Resume preview"
      >
        <p>Select a saved resume version to see it here.</p>
      </article>
    );
  }

  const sections = buildSections(snapshot);

  return (
    <article
      className={`resume-preview resume-preview--${template}`}
      aria-label="Resume preview"
    >
      <header>
        <h3>{fullName || "Your name"}</h3>
        {targetRole && <p>{targetRole}</p>}
        {company && <p>Target company: {company}</p>}
      </header>

      {sections.length === 0 ? (
        <p>This version has no statements to show.</p>
      ) : (
        sections.map((section) => (
          <section key={section.heading}>
            <h4>{section.heading}</h4>
            {section.entries.map((entry, index) => {
              const label = entryLabel(entry);
              return (
                <div key={`${section.heading}:${index}`}>
                  {label && (
                    <p>
                      <strong>{label}</strong>
                    </p>
                  )}
                  <ul>
                    {entry.bullets.map((bullet, position) => (
                      <li key={position}>{bullet}</li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </section>
        ))
      )}
    </article>
  );
}
