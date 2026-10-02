/**
 * Sample data for the prototype pages.
 *
 * Every screen except Tailoring runs on this until its owner's feature is
 * merged. Tailoring calls the real F07 backend — see features/tailoring/api.ts.
 */

export interface MockEvidence {
  id: string;
  ref: string;
  type: string;
  title: string;
  organization?: string;
  dates?: string;
  detail: string;
  status: "APPROVED" | "UNCONFIRMED";
}

export const EVIDENCE: MockEvidence[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    ref: "E1",
    type: "Work experience",
    title: "Associate QA Engineer",
    organization: "Model N",
    dates: "Jun 2022 – Dec 2024",
    detail:
      "Built automated regression suites for revenue management software and owned release-candidate test cycles.",
    status: "APPROVED",
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    ref: "E2",
    type: "Skill",
    title: "Python",
    detail: "Used for test automation and backend services.",
    status: "APPROVED",
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    ref: "E3",
    type: "Project",
    title: "ApplyWise capstone backend",
    organization: "Texas A&M University–Corpus Christi",
    detail:
      "Designed a FastAPI service with a grounded generation module and wrote a 29-test suite.",
    status: "APPROVED",
  },
  {
    id: "44444444-4444-4444-4444-444444444444",
    ref: "E4",
    type: "Accomplishment",
    title: "Reduced release defects by 40%",
    detail: "Imported from resume_2026.pdf. Confirm the figure before approving.",
    status: "UNCONFIRMED",
  },
];

export interface MockRequirement {
  name: string;
  kind: "Required" | "Preferred";
  support: "Strong" | "Partial" | "Gap";
  supportedBy: string[];
  note: string;
}

export const REQUIREMENTS: MockRequirement[] = [
  {
    name: "Test automation",
    kind: "Required",
    support: "Strong",
    supportedBy: ["E1", "E2"],
    note: "Named directly in your QA role and your Python skill.",
  },
  {
    name: "Python",
    kind: "Required",
    support: "Strong",
    supportedBy: ["E2", "E3"],
    note: "Backed by a skill entry and a project.",
  },
  {
    name: "REST API testing",
    kind: "Required",
    support: "Partial",
    supportedBy: ["E1"],
    note: "Your evidence mentions API tests but gives no detail.",
  },
  {
    name: "Performance testing",
    kind: "Preferred",
    support: "Gap",
    supportedBy: [],
    note: "No approved evidence. ApplyWise will not write about it.",
  },
  {
    name: "Kubernetes",
    kind: "Preferred",
    support: "Gap",
    supportedBy: [],
    note: "No approved evidence. Add real evidence or leave the gap.",
  },
];

export interface MockReviewStatement {
  id: string;
  text: string;
  state: "VERIFIED" | "INFERRED" | "UNSUPPORTED";
  refs: string[];
  note: string;
}

export const REVIEW_STATEMENTS: MockReviewStatement[] = [
  {
    id: "s1",
    text: "Built and maintained automated regression suites for revenue management software, supporting release-candidate test cycles.",
    state: "VERIFIED",
    refs: ["E1"],
    note: "Every claim appears in the cited evidence.",
  },
  {
    id: "s2",
    text: "Wrote Python test automation for a backend service delivered by a six-person team.",
    state: "VERIFIED",
    refs: ["E2", "E3"],
    note: "Every claim appears in the cited evidence.",
  },
  {
    id: "s3",
    text: "Owned end-to-end quality for a revenue platform used by enterprise customers.",
    state: "INFERRED",
    refs: ["E1"],
    note: "Your evidence says you built regression suites and owned test cycles — not that you owned quality end to end.",
  },
  {
    id: "s4",
    text: "Improved release quality by 40% across the product line.",
    state: "UNSUPPORTED",
    refs: [],
    note: "The 40% figure sits in an unconfirmed imported item, not in approved evidence.",
  },
];

export interface MockApplication {
  company: string;
  role: string;
  stage: "Saved" | "Applied" | "Interviewing" | "Closed";
  when: string;
  version: string;
}

export const APPLICATIONS: MockApplication[] = [
  { company: "Example Corp", role: "Software Engineer in Test", stage: "Saved", when: "today", version: "v3" },
  { company: "Northline Health", role: "QA Automation Engineer", stage: "Saved", when: "2 days ago", version: "v1" },
  { company: "Harbor Systems", role: "SDET II", stage: "Applied", when: "22 Sep", version: "v2" },
  { company: "Bluefield Labs", role: "Quality Engineer", stage: "Applied", when: "19 Sep", version: "v1" },
  { company: "Cadence Retail", role: "Test Engineer, Platform", stage: "Applied", when: "15 Sep", version: "v1" },
  { company: "Meridian Software", role: "QA Engineer II", stage: "Interviewing", when: "round 2 on 3 Oct", version: "v2" },
  { company: "Verra Group", role: "Automation Analyst", stage: "Closed", when: "no response, 4 Sep", version: "v1" },
];

export const DIARY = [
  {
    quote:
      "I stopped rewriting the same bullet for the fifth time. It showed me which job needed which fact, and I just picked.",
    who: "Priya, graduate student",
  },
  {
    quote:
      "The part I trust is the little tag on every line. I know where it came from, so I can defend it in the room.",
    who: "Marcus, career changer",
  },
];

export const FAQ = [
  {
    q: "Does ApplyWise write my resume for me?",
    a: "It drafts statements from facts you have approved, and shows which fact each statement came from. You approve every line before it reaches a resume.",
  },
  {
    q: "What stops it from inventing things?",
    a: "Generated text must cite the evidence it used. Anything citing a source you did not supply is discarded before you see it, and anything unsupported is blocked from export.",
  },
  {
    q: "Who can see my evidence profile?",
    a: "Only you. A reviewer link shows one resume version and its comments — never the profile behind it.",
  },
];
