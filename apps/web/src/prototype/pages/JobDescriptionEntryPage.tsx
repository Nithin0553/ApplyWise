import { useState, type FormEvent } from "react";

interface JobDescriptionEntryPageProps {
  onContinue: (jobDescription: string) => void;
}

/**
 * The signed-in starting point. This collects only the user's own job
 * description; it does not claim to analyse it or call the backend.
 */
export function JobDescriptionEntryPage({ onContinue }: JobDescriptionEntryPageProps) {
  const [description, setDescription] = useState("");
  const canContinue = description.trim().length > 0;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (canContinue) {
      onContinue(description.trim());
    }
  };

  return (
    <main className="sf-jd-main">
      <form className="sf-jd-form" onSubmit={submit}>
        <label htmlFor="sf-job-description" className="sf-jd-label">
          Paste your job description to ApplyWise
        </label>
        <div className="sf-jd-glow-wrap">
          <div className="sf-jd-input-shell">
            <textarea
              id="sf-job-description"
              className="sf-jd-input"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              autoComplete="off"
              spellCheck
              rows={7}
              placeholder="Paste the job description here..."
            />
          </div>
        </div>
        {canContinue && (
          <button type="submit" className="sf-jd-continue">
            Continue <span aria-hidden="true">→</span>
          </button>
        )}
      </form>
    </main>
  );
}
