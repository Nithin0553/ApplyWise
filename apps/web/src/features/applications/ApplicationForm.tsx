import type { FormEvent } from "react";

import "./applications.css";

import type { ApplicationFormValues } from "./types";

const EMPTY_APPLICATION_FORM: ApplicationFormValues = {
  companyName: "",
  roleTitle: "",
  location: "",
  jobUrl: "",
  source: "",
  notes: "",
  appliedOn: "",
  nextActionOn: "",
};

interface ApplicationFormProps {
  initialValues?: Partial<ApplicationFormValues>;
  submitLabel?: string;
  onSubmit: (values: ApplicationFormValues) => void;
  onCancel?: () => void;
}

function readText(formData: FormData, name: keyof ApplicationFormValues): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

export function ApplicationForm({
  initialValues,
  submitLabel = "Save application",
  onSubmit,
  onCancel,
}: ApplicationFormProps) {
  const values = { ...EMPTY_APPLICATION_FORM, ...initialValues };

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    onSubmit({
      companyName: readText(formData, "companyName"),
      roleTitle: readText(formData, "roleTitle"),
      location: readText(formData, "location"),
      jobUrl: readText(formData, "jobUrl"),
      source: readText(formData, "source"),
      notes: readText(formData, "notes"),
      appliedOn: readText(formData, "appliedOn"),
      nextActionOn: readText(formData, "nextActionOn"),
    });
  }

  return (
    <form className="application-form" onSubmit={handleSubmit}>
      <div className="application-form__grid">
        <label>
          Company
          <input
            name="companyName"
            defaultValue={values.companyName}
            maxLength={200}
            required
          />
        </label>
        <label>
          Role title
          <input
            name="roleTitle"
            defaultValue={values.roleTitle}
            maxLength={200}
            required
          />
        </label>
        <label>
          Location
          <input name="location" defaultValue={values.location} maxLength={200} />
        </label>
        <label>
          Job link
          <input
            name="jobUrl"
            defaultValue={values.jobUrl}
            maxLength={1000}
            type="url"
          />
        </label>
        <label>
          Source
          <input name="source" defaultValue={values.source} maxLength={100} />
        </label>
        <label>
          Applied date
          <input name="appliedOn" defaultValue={values.appliedOn} type="date" />
        </label>
        <label>
          Next action date
          <input
            name="nextActionOn"
            defaultValue={values.nextActionOn}
            type="date"
          />
        </label>
        <label className="application-form__wide">
          Notes
          <textarea name="notes" defaultValue={values.notes} rows={4} />
        </label>
      </div>

      <div className="application-form__actions">
        {onCancel ? (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        ) : null}
        <button type="submit">{submitLabel}</button>
      </div>
    </form>
  );
}
