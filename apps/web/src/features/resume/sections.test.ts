// Grouping rule for the resume preview. It mirrors the server's F10 adapter,
// so these cases pin the same two properties the Python tests pin: the
// section comes from the cited evidence's type, and the highest-ranking type
// wins when a statement cites several.
import { describe, expect, it } from "vitest";

import type {
  EvidenceSnapshotItem, ProvenanceSnapshotItem, ResumeVersionSnapshot,
} from "../applications/api";
import { buildSections, entryLabel, isTrustedVersion } from "./sections";

const record = (
  id: string, evidence_type: string,
  organization: string | null = null, role: string | null = null,
): EvidenceSnapshotItem => ({
  evidence_id: id, evidence_type, title: id,
  organization, role, description: null,
  approved_at: "2026-11-15T00:00:00Z",
});

const claim = (
  text: string, ids: string[],
  origin: "F09_APPROVED" | "DRAFT_USER_REVIEWED" = "F09_APPROVED",
): ProvenanceSnapshotItem => ({
  statement_id: text, text, evidence_ids: ids,
  verification_status: "VERIFIED", approval_status: "APPROVED", origin,
});

const snapshot = (
  evidence: EvidenceSnapshotItem[], statements: ProvenanceSnapshotItem[],
): ResumeVersionSnapshot => ({
  user_id: "u", application_id: "a", resume_version_id: "v",
  created_at: "2026-11-15T00:00:00Z", evidence, statements,
});

describe("buildSections", () => {
  it("files each claim by the kind of evidence it cites", () => {
    const result = buildSections(snapshot(
      [record("job", "work_experience", "Model N", "Associate QA Engineer"),
       record("cert", "certification"),
       record("py", "skill")],
      [claim("Built regression suites.", ["job"]),
       claim("Hold ISTQB Foundation Level.", ["cert"]),
       claim("Advanced Python.", ["py"])],
    ));

    expect(result.map((section) => section.heading)).toEqual([
      "Professional Experience", "Certifications", "Technical Skills",
    ]);
  });

  it("keeps the section order fixed regardless of approval order", () => {
    const result = buildSections(snapshot(
      [record("py", "skill"), record("job", "work_experience", "Model N", "QA")],
      [claim("Advanced Python.", ["py"]), claim("Built regression suites.", ["job"])],
    ));

    expect(result[0].heading).toBe("Professional Experience");
  });

  it("collects one employer's claims under a single entry", () => {
    const result = buildSections(snapshot(
      [record("job", "work_experience", "Model N", "Associate QA Engineer")],
      [claim("Built regression suites.", ["job"]),
       claim("Owned release-candidate cycles.", ["job"])],
    ));

    expect(result[0].entries).toHaveLength(1);
    expect(result[0].entries[0].bullets).toHaveLength(2);
    expect(entryLabel(result[0].entries[0])).toBe("Associate QA Engineer, Model N");
  });

  it("files a responsibility under the job it cites", () => {
    const result = buildSections(snapshot(
      [record("duty", "responsibility"),
       record("job", "work_experience", "Model N", "QA")],
      [claim("Signed off releases.", ["duty", "job"])],
    ));

    expect(result.map((section) => section.heading)).toEqual(["Professional Experience"]);
  });

  it("leaves the label empty when the evidence has no organization or role", () => {
    const result = buildSections(snapshot(
      [record("cert", "certification")],
      [claim("Hold ISTQB Foundation Level.", ["cert"])],
    ));

    expect(entryLabel(result[0].entries[0])).toBe("");
  });
});

describe("isTrustedVersion", () => {
  it("accepts a version whose statements all came through F09", () => {
    expect(isTrustedVersion(snapshot(
      [record("job", "work_experience")], [claim("Built suites.", ["job"])],
    ))).toBe(true);
  });

  it("rejects a saved draft", () => {
    expect(isTrustedVersion(snapshot(
      [record("job", "work_experience")],
      [claim("Built suites.", ["job"], "DRAFT_USER_REVIEWED")],
    ))).toBe(false);
  });

  it("rejects a version with no statements", () => {
    expect(isTrustedVersion(snapshot([], []))).toBe(false);
  });
});
