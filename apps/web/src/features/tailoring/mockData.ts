import type { EvidenceOption, GenerationResult, JobContext } from "./types";

/**
 * Fallback list for the evidence picker when USE_REAL.f02_evidence is false.
 *
 * These ids exist only in the browser. With the flag on, the picker shows the
 * user's real approved evidence and the server resolves the selected ids, so
 * none of these would resolve to anything.
 */
export const MOCK_APPROVED_EVIDENCE: EvidenceOption[] = [
  {
    evidence_id: "11111111-1111-1111-1111-111111111111",
    evidence_type: "work_experience",
    title: "Associate QA Engineer",
    organization: "Model N",
    description:
      "Built automated regression suites for revenue management software and owned release-candidate test cycles.",
  },
  {
    evidence_id: "22222222-2222-2222-2222-222222222222",
    evidence_type: "skill",
    title: "Python",
    description: "Used for test automation and backend services.",
  },
  {
    evidence_id: "33333333-3333-3333-3333-333333333333",
    evidence_type: "project",
    title: "ApplyWise capstone backend",
    organization: "Texas A&M University–Corpus Christi",
    description:
      "FastAPI service with a grounded generation module and a 29-test suite, built with a six-person team.",
  },
];

export const MOCK_JOB_CONTEXT: JobContext = {
  job_title: "Software Engineer in Test",
  company: "Example Corp",
  description:
    "Own automated testing for a Python backend. Design and maintain automated regression suites and improve release readiness.",
  requirements: ["Python", "test automation", "REST API testing"],
};

/** Used only when USE_REAL.f07_generation is false. */
export const MOCK_GENERATION_RESULT: GenerationResult = {
  generation_id: "00000000-0000-0000-0000-00000000000f",
  user_id: "00000000-0000-0000-0000-0000000000aa",
  provider: "mock (no backend)",
  generated_at: new Date().toISOString(),
  statements: [
    {
      statement_id: "00000000-0000-0000-0000-000000000001",
      text: "Built and maintained automated regression suites for revenue management software, supporting release-candidate test cycles.",
      evidence_ids: ["11111111-1111-1111-1111-111111111111"],
      status: "CANDIDATE",
      verification_status: "PENDING",
      approval_status: "UNREVIEWED",
      export_eligible: false,
    },
    {
      statement_id: "00000000-0000-0000-0000-000000000002",
      text: "Wrote Python test automation for a backend service delivered by a six-person team.",
      evidence_ids: [
        "22222222-2222-2222-2222-222222222222",
        "33333333-3333-3333-3333-333333333333",
      ],
      status: "CANDIDATE",
      verification_status: "PENDING",
      approval_status: "UNREVIEWED",
      export_eligible: false,
    },
  ],
  rejected: [
    {
      text: "Reduced production incidents by 40% through an automated release gate.",
      reason: "cites unknown evidence reference 'E9'",
    },
  ],
};
