import { useState, type FormEvent } from "react";

const MAX_DESCRIPTION_LENGTH = 6000;

interface JobDescriptionEntryPageProps {
  onContinue: (jobDescription: string) => void;
}

/**
 * Signed-in starting point. Content remains local to this UI until the user
 * continues; job analysis is a separate step and must not be implied here.
 */
export function JobDescriptionEntryPage({ onContinue }: JobDescriptionEntryPageProps) {
  const [description, setDescription] = useState("");
  const canContinue = description.trim().length > 0;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (canContinue) onContinue(description.trim());
  };

  return (
    <main className="sf-jd-main">
      <form className="sf-jd-form" onSubmit={submit}>
        <h2 id="sf-jd-heading" className="sf-jd-label">
          Paste your job description to{" "}
          <span className="sf-jd-title-light" data-text="ApplyWise">ApplyWise</span>
        </h2>

        <div className="sf-jd-glow-wrap">
          <div className="sf-jd-input-shell">
            <textarea
              id="sf-job-description"
              aria-labelledby="sf-jd-heading"
              aria-describedby="sf-jd-hint sf-jd-counter"
              className="sf-jd-input"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              autoComplete="off"
              spellCheck
              rows={7}
              maxLength={MAX_DESCRIPTION_LENGTH}
              placeholder="Paste the full job description here..."
            />
            <span id="sf-jd-counter" className="sf-jd-counter" aria-live="off">
              {description.length} / {MAX_DESCRIPTION_LENGTH}
            </span>
          </div>
        </div>

        <p className="sf-jd-privacy">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
            strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="5" y="10" width="14" height="11" rx="2" />
            <path d="M8 10V7a4 4 0 0 1 8 0v3" />
          </svg>
          Your job description stays in this session until you continue.
        </p>

        <div className="sf-jd-actions">
          <button type="submit" className="sf-jd-continue" disabled={!canContinue}>
            Continue <span aria-hidden="true">→</span>
          </button>
          <button type="button" className="sf-jd-clear" disabled={!description.length}
            onClick={() => setDescription("")}>
            Clear
          </button>
        </div>

        <p id="sf-jd-hint" className="sf-jd-tip">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"
            strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 18h6m-5 3h4M9 15c0-2-4-3-4-8a7 7 0 0 1 14 0c0 5-4 6-4 8l-1 1h-4z" />
          </svg>
          <span><strong>Tip:</strong> Include the full role summary, responsibilities, and requirements for better tailoring.</span>
        </p>
      </form>
    </main>
  );
}
