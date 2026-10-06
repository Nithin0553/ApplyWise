import { useState } from "react";
import type { FormEvent } from "react";

import "./evidence.css";

import { EVIDENCE_TYPE_OPTIONS } from "./types";
import type { EvidenceFormValues, EvidenceType } from "./types";

const EMPTY_EVIDENCE_FORM: EvidenceFormValues = {
  evidenceType: "work_experience",
  title: "",
  organization: "",
  role: "",
  location: "",
  description: "",
  skillName: "",
  proficiency: "",
  credential: "",
  url: "",
  startDate: "",
  endDate: "",
  source: "",
};

interface EvidenceFormProps {
  initialValues?: Partial<EvidenceFormValues>;
  submitLabel?: string;
  busy?: boolean;
  approvalWillBeRevoked?: boolean;
  onSubmit: (values: EvidenceFormValues) => void | Promise<void>;
  onCancel?: () => void;
}

function readText(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function readEvidenceType(formData: FormData): EvidenceType {
  const value = readText(formData, "evidenceType") as EvidenceType;
  return EVIDENCE_TYPE_OPTIONS.some((option) => option.value === value)
    ? value
    : "work_experience";
}

export function EvidenceForm({
  initialValues,
  submitLabel = "Save evidence",
  busy = false,
  approvalWillBeRevoked = false,
  onSubmit,
  onCancel,
}: EvidenceFormProps) {
  const values = { ...EMPTY_EVIDENCE_FORM, ...initialValues };
  const [validationError, setValidationError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const title = readText(formData, "title");
    const url = readText(formData, "url");
    const startDate = readText(formData, "startDate");
    const endDate = readText(formData, "endDate");

    if (!title) {
      setValidationError("Title is required.");
      return;
    }

    if (url && !/^https?:\/\//i.test(url)) {
      setValidationError("Supporting link must start with http:// or https://.");
      return;
    }

    if (startDate && endDate && endDate < startDate) {
      setValidationError("End date cannot be earlier than start date.");
      return;
    }

    setValidationError(null);
    void onSubmit({
      evidenceType: readEvidenceType(formData),
      title,
      organization: readText(formData, "organization"),
      role: readText(formData, "role"),
      location: readText(formData, "location"),
      description: readText(formData, "description"),
      skillName: readText(formData, "skillName"),
      proficiency: readText(formData, "proficiency"),
      credential: readText(formData, "credential"),
      url,
      startDate,
      endDate,
      source: readText(formData, "source"),
    });
  }

  return (
    <form className="evidence-form" onSubmit={handleSubmit}>
      {approvalWillBeRevoked ? (
        <p className="evidence-form__warning" role="note">
          This evidence is approved. Saving a real change will return it to
          unconfirmed status so it can be reviewed again.
        </p>
      ) : null}

      {validationError ? (
        <p className="evidence-form__error" role="alert">
          {validationError}
        </p>
      ) : null}

      <div className="evidence-form__grid">
        <label>
          Evidence type
          <select name="evidenceType" defaultValue={values.evidenceType} disabled={busy}>
            {EVIDENCE_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          Title
          <input
            name="title"
            defaultValue={values.title}
            maxLength={200}
            required
            disabled={busy}
          />
        </label>

        <label>
          Organization
          <input
            name="organization"
            defaultValue={values.organization}
            maxLength={200}
            disabled={busy}
          />
        </label>

        <label>
          Role
          <input
            name="role"
            defaultValue={values.role}
            maxLength={200}
            disabled={busy}
          />
        </label>

        <label>
          Location
          <input
            name="location"
            defaultValue={values.location}
            maxLength={200}
            disabled={busy}
          />
        </label>

        <label>
          Source
          <input
            name="source"
            defaultValue={values.source}
            maxLength={100}
            placeholder="Manual entry, resume import, portfolio..."
            disabled={busy}
          />
        </label>

        <label>
          Start date
          <input name="startDate" type="date" defaultValue={values.startDate} disabled={busy} />
        </label>

        <label>
          End date
          <input name="endDate" type="date" defaultValue={values.endDate} disabled={busy} />
        </label>

        <label>
          Skill name
          <input
            name="skillName"
            defaultValue={values.skillName}
            maxLength={200}
            disabled={busy}
          />
        </label>

        <label>
          Proficiency
          <input
            name="proficiency"
            defaultValue={values.proficiency}
            maxLength={100}
            disabled={busy}
          />
        </label>

        <label>
          Credential
          <input
            name="credential"
            defaultValue={values.credential}
            maxLength={200}
            disabled={busy}
          />
        </label>

        <label>
          Supporting link
          <input
            name="url"
            type="url"
            defaultValue={values.url}
            maxLength={500}
            placeholder="https://..."
            disabled={busy}
          />
        </label>

        <label className="evidence-form__wide">
          Description
          <textarea
            name="description"
            defaultValue={values.description}
            rows={5}
            disabled={busy}
          />
        </label>
      </div>

      <div className="evidence-form__actions">
        {onCancel ? (
          <button type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        ) : null}
        <button type="submit" disabled={busy}>
          {busy ? "Saving..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
