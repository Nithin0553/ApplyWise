import type { EvidenceFormValues, EvidenceItem, EvidenceStatus, EvidenceType } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface EvidenceApiRecord {
  id: string;
  user_id: string;
  evidence_type: EvidenceType;
  title: string;
  organization: string | null;
  role: string | null;
  location: string | null;
  description: string | null;
  skill_name: string | null;
  proficiency: string | null;
  credential: string | null;
  url: string | null;
  start_date: string | null;
  end_date: string | null;
  source: string | null;
  status: EvidenceStatus;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export class EvidenceApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "EvidenceApiError";
    this.status = status;
  }
}

function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function toPayload(values: EvidenceFormValues) {
  return {
    evidence_type: values.evidenceType,
    title: values.title.trim(),
    organization: nullable(values.organization),
    role: nullable(values.role),
    location: nullable(values.location),
    description: nullable(values.description),
    skill_name: nullable(values.skillName),
    proficiency: nullable(values.proficiency),
    credential: nullable(values.credential),
    url: nullable(values.url),
    start_date: nullable(values.startDate),
    end_date: nullable(values.endDate),
    source: nullable(values.source),
  };
}

function toEvidenceItem(record: EvidenceApiRecord): EvidenceItem {
  return {
    id: record.id,
    evidenceType: record.evidence_type,
    title: record.title,
    organization: record.organization ?? "",
    role: record.role ?? "",
    location: record.location ?? "",
    description: record.description ?? "",
    skillName: record.skill_name ?? "",
    proficiency: record.proficiency ?? "",
    credential: record.credential ?? "",
    url: record.url ?? "",
    startDate: record.start_date ?? "",
    endDate: record.end_date ?? "",
    source: record.source ?? "",
    status: record.status,
    approvedAt: record.approved_at,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail)) {
        return detail
          .map((item) =>
            item && typeof item === "object" && "msg" in item ? String(item.msg) : null,
          )
          .filter((message): message is string => Boolean(message))
          .join(" ");
      }
    }
  } catch {
    // Fall through to a generic status-based message.
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new EvidenceApiError(await extractErrorMessage(response), response.status);
  }
  return (await response.json()) as T;
}

export async function listEvidence(token: string): Promise<EvidenceItem[]> {
  const records = await request<EvidenceApiRecord[]>("/api/evidence/", token);
  return records.map(toEvidenceItem);
}

export async function createEvidence(
  token: string,
  values: EvidenceFormValues,
): Promise<EvidenceItem> {
  const record = await request<EvidenceApiRecord>("/api/evidence/", token, {
    method: "POST",
    body: JSON.stringify(toPayload(values)),
  });
  return toEvidenceItem(record);
}

export async function updateEvidence(
  token: string,
  evidenceId: string,
  values: EvidenceFormValues,
): Promise<EvidenceItem> {
  const record = await request<EvidenceApiRecord>(`/api/evidence/${evidenceId}`, token, {
    method: "PATCH",
    body: JSON.stringify(toPayload(values)),
  });
  return toEvidenceItem(record);
}

export async function approveEvidence(token: string, evidenceId: string): Promise<EvidenceItem> {
  const record = await request<EvidenceApiRecord>(
    `/api/evidence/${evidenceId}/approve`,
    token,
    { method: "POST" },
  );
  return toEvidenceItem(record);
}

export async function unconfirmEvidence(
  token: string,
  evidenceId: string,
): Promise<EvidenceItem> {
  const record = await request<EvidenceApiRecord>(
    `/api/evidence/${evidenceId}/unconfirm`,
    token,
    { method: "POST" },
  );
  return toEvidenceItem(record);
}
