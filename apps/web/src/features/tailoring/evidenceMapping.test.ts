/**
 * F02 -> evidence picker translation.
 *
 * Since evidence selection moved server-side, this mapping feeds the picker
 * only. The id is the one load-bearing field: it is what the generation
 * request sends, and the server reads the record itself from F02. The tests
 * below pin that down — including that the mapper carries no approval state
 * and no generation content, so nothing in the browser can assert either.
 *
 * Payloads are shaped like ApprovedEvidence in
 * apps/api/app/modules/evidence/schemas.py, including F02's lowercase enum.
 */

import { describe, expect, it } from "vitest";

import { ApiError, toEvidenceOption } from "./api";

const WORK_RECORD = {
  id: "11111111-1111-1111-1111-111111111111",
  user_id: "99999999-9999-9999-9999-999999999999",
  evidence_type: "work_experience",
  title: "Associate QA Engineer",
  organization: "Model N",
  role: "Associate QA Engineer",
  location: "Hyderabad, India",
  description: "Built automated regression suites.",
  status: "approved",
  approved_at: "2026-09-21T10:00:00Z",
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-21T10:00:00Z",
};

const SKILL_RECORD = {
  id: "22222222-2222-2222-2222-222222222222",
  evidence_type: "skill",
  title: "Python",
  skill_name: "Python",
  proficiency: "Advanced",
};

describe("toEvidenceOption", () => {
  it("maps F02's id onto the evidence_id the request sends", () => {
    const mapped = toEvidenceOption(WORK_RECORD);

    expect(mapped.evidence_id).toBe(WORK_RECORD.id);
    // The failure this guards against: a cast leaves evidence_id undefined,
    // and the request then selects nothing the server can resolve.
    expect(mapped.evidence_id).not.toBeUndefined();
  });

  it("keeps the fields the picker shows", () => {
    const mapped = toEvidenceOption(WORK_RECORD);

    expect(mapped.title).toBe("Associate QA Engineer");
    expect(mapped.organization).toBe("Model N");
    expect(mapped.evidence_type).toBe("work_experience");
  });

  it("carries no approval state into the browser's model", () => {
    const mapped = toEvidenceOption(WORK_RECORD) as unknown as Record<string, unknown>;

    // Approval is decided server-side when the ids are resolved. Nothing the
    // browser holds should be able to assert it.
    expect(mapped.status).toBeUndefined();
    expect(mapped.approved_at).toBeUndefined();
    expect(mapped.user_id).toBeUndefined();
  });

  it("carries no generation content either", () => {
    const mapped = toEvidenceOption(SKILL_RECORD) as unknown as Record<string, unknown>;

    // skill_name and proficiency reach the AI provider, so they must come from
    // the server's own read of the record, never from this object.
    expect(mapped.skill_name).toBeUndefined();
    expect(mapped.proficiency).toBeUndefined();
  });

  it("refuses a record with no id, because nothing could select it", () => {
    expect(() => toEvidenceOption({ ...WORK_RECORD, id: undefined })).toThrow(ApiError);
  });

  it("refuses a record with no title", () => {
    expect(() => toEvidenceOption({ ...WORK_RECORD, title: undefined })).toThrow(ApiError);
  });
});
