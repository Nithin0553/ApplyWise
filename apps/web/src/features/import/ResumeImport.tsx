// F03: upload a PDF or Word resume and receive proposed, unconfirmed evidence records.

import { useRef, useState } from "react";
import type { FormEvent } from "react";

import { EvidenceApiError, importResume } from "../evidence/api";
import type { EvidenceItem } from "../evidence/types";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];
const MAX_BYTES = 5 * 1024 * 1024;

interface ResumeImportProps {
  token: string;
  onImported: (items: EvidenceItem[]) => void;
  onCancel?: () => void;
}

function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return "Only PDF (.pdf) and Word (.docx) resumes can be imported.";
  }
  if (file.size > MAX_BYTES) {
    return "This file is larger than 5 MB. Upload a smaller PDF or Word resume.";
  }
  return null;
}

export function ResumeImport({ token, onImported, onCancel }: ResumeImportProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const file = inputRef.current?.files?.[0];
    if (!file) {
      setError("Choose a PDF or Word (.docx) resume to import.");
      return;
    }
    const problem = validateFile(file);
    if (problem) {
      setError(problem);
      return;
    }

    setIsUploading(true);
    try {
      const items = await importResume(token, file);
      setMessage(
        `Imported ${items.length} proposed ${items.length === 1 ? "record" : "records"}. ` +
          "They are unconfirmed: review, correct, and approve each one before it can be used.",
      );
      if (inputRef.current) {
        inputRef.current.value = "";
      }
      onImported(items);
    } catch (importError) {
      setError(
        importError instanceof EvidenceApiError
          ? importError.message
          : "The resume could not be imported. Please try again or add your evidence manually.",
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <form className="resume-import" onSubmit={(event) => void handleSubmit(event)}>
      <label htmlFor="resume-import-file">Resume file (PDF or Word .docx, up to 5 MB)</label>
      <input
        id="resume-import-file"
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        disabled={isUploading}
      />

      {error ? (
        <p role="alert" className="resume-import__error">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="resume-import__message">
          {message}
        </p>
      ) : null}

      <div className="resume-import__actions">
        <button type="submit" disabled={isUploading}>
          {isUploading ? "Importing…" : "Import resume"}
        </button>
        {onCancel ? (
          <button type="button" onClick={onCancel} disabled={isUploading}>
            Close
          </button>
        ) : null}
      </div>
    </form>
  );
}
