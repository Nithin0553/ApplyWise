import type { ResumeDocument } from "./api";

type ResumePreviewProps = {
  template: string;
  document: ResumeDocument;
};

export function ResumePreview({ template, document }: ResumePreviewProps) {
  return (
    <article
      className={`resume-preview resume-preview--${template}`}
      aria-label="Validated resume preview"
    >
      <header>
        <h3>{document.full_name}</h3>
        <p>{document.target_role}</p>
        {document.company && <p>Target company: {document.company}</p>}
      </header>
      {document.sections.map((section) => (
        <section key={section.heading}>
          <h4>{section.heading}</h4>
          {section.entries.map((entry, index) => {
            const heading = [...new Set(
              [entry.title, entry.role, entry.organization].filter(Boolean),
            )].join(" | ");
            let dates = [entry.start_date, entry.end_date].filter(Boolean).join(" - ");
            if (dates && !entry.start_date) dates = `Ended ${dates}`;
            else if (dates && !entry.end_date) dates = `Started ${dates}`;
            return (
              <div key={index}>
                {heading && <p><strong>{heading}</strong></p>}
                {dates && <p>{dates}</p>}
                {entry.statements.length > 0 && (
                  <ul>{entry.statements.map((text, i) => <li key={i}>{text}</li>)}</ul>
                )}
              </div>
            );
          })}
        </section>
      ))}
    </article>
  );
}
