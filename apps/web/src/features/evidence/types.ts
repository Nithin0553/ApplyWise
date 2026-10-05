export type EvidenceType =
  | "work_experience"
  | "education"
  | "project"
  | "skill"
  | "certification"
  | "responsibility"
  | "accomplishment"
  | "supporting_detail";

export type EvidenceStatus = "unconfirmed" | "approved";

export interface EvidenceFormValues {
  evidenceType: EvidenceType;
  title: string;
  organization: string;
  role: string;
  location: string;
  description: string;
  skillName: string;
  proficiency: string;
  credential: string;
  url: string;
  startDate: string;
  endDate: string;
  source: string;
}

export interface EvidenceItem extends EvidenceFormValues {
  id: string;
  status: EvidenceStatus;
  approvedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export const EVIDENCE_TYPE_OPTIONS: ReadonlyArray<{
  value: EvidenceType;
  label: string;
}> = [
  { value: "work_experience", label: "Work experience" },
  { value: "education", label: "Education" },
  { value: "project", label: "Project" },
  { value: "skill", label: "Skill" },
  { value: "certification", label: "Certification" },
  { value: "responsibility", label: "Responsibility" },
  { value: "accomplishment", label: "Accomplishment" },
  { value: "supporting_detail", label: "Supporting detail" },
];

export function evidenceTypeLabel(value: EvidenceType): string {
  return EVIDENCE_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export function toEvidenceFormValues(item: EvidenceItem): EvidenceFormValues {
  return {
    evidenceType: item.evidenceType,
    title: item.title,
    organization: item.organization,
    role: item.role,
    location: item.location,
    description: item.description,
    skillName: item.skillName,
    proficiency: item.proficiency,
    credential: item.credential,
    url: item.url,
    startDate: item.startDate,
    endDate: item.endDate,
    source: item.source,
  };
}
