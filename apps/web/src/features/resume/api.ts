export type ResumeExportFormat = "pdf" | "docx";
export type ResumeExportTemplate = "standard" | "compact";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ResumeExportError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ResumeExportError";
    this.status = status;
  }
}

function exportErrorMessage(status: number): string {
  switch (status) {
    case 401:
      return "Your session has expired. Please sign in again.";
    case 403:
      return "You do not have permission to export this resume.";
    case 404:
      return "This resume version could not be found.";
    case 409:
      return "This resume requires updated verification or approval before downloading.";
    case 503:
      return "Resume verification is temporarily unavailable. Please try again later.";
    default:
      return "Unable to download your resume. Please try again.";
  }
}

export async function downloadResume(
  token: string,
  resumeVersionId: string,
  format: ResumeExportFormat,
  template: ResumeExportTemplate,
): Promise<Blob> {
  const params = new URLSearchParams({
    format,
    template,
  });

  const path =
    `/api/documents/resume-versions/${encodeURIComponent(resumeVersionId)}/export`;

  const response = await fetch(
    `${API_BASE_URL}${path}?${params.toString()}`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );

  if (!response.ok) {
    throw new ResumeExportError(
      exportErrorMessage(response.status),
      response.status,
    );
  }

  return response.blob();
}
