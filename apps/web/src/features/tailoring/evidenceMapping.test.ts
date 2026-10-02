/**
 * F02 -> F07 evidence translation.
 *
 * F02 returns records keyed by `id`; F07 cites evidence by `evidence_id`.
 * Casting one to the other compiles and then fails silently at runtime, which
 * is the bug these tests exist to prevent. The payloads below are shaped like
 * ApprovedEvidence in apps/api/app/modules/evidence/schemas.py, including F02's
 * lowercase enum values.
 */

import { describe, expect, it } from "vitest";

import { ApiError, toGenerationEvidence } from "./api";

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

describe("toGenerationEvidence", () => {
  it("maps F02's id onto F07's evidence_id", () => {
    const mapped = toGenerationEvidence(WORK_RECORD);

    expect(mapped.evidence_id).toBe(WORK_RECORD.id);
    // The failure this guards against: a cast leaves evidence_id undefined,
    // which renders as "E?" and sends a request the backend cannot ground.
    expect(mapped.evidence_id).not.toBeUndefined();
  });

  it("normalises F02's lowercase enum to the type F07 labels evidence with", () => {
    expect(toGenerationEvidence(WORK_RECORD).evidence_type).toBe("WORK_EXPERIENCE");
    expect(toGenerationEvidence(SKILL_RECORD).evidence_type).toBe("SKILL");
  });

  it("keeps the structured fields that carry a skill's meaning", () => {
    const mapped = toGenerationEvidence(SKILL_RECORD);

    expect(mapped.skill_name).toBe("Python");
    expect(mapped.proficiency).toBe("Advanced");
    // No description on skill evidence: absent fields become null, not undefined.
    expect(mapped.description).toBeNull();
  });

  it("drops F02 fields F07 must not generate from", () => {
    const mapped = toGenerationEvidence(WORK_RECORD) as unknown as Record<string, unknown>;

    // Provenance metadata and ownership are not content for the provider.
    expect(mapped.status).toBeUndefined();
    expect(mapped.approved_at).toBeUndefined();
    expect(mapped.user_id).toBeUndefined();
  });

  it("refuses a record with no id, because nothing could cite it", () => {
    expect(() => toGenerationEvidence({ ...WORK_RECORD, id: undefined })).toThrow(ApiError);
  });

  it("refuses a record with no title", () => {
    expect(() => toGenerationEvidence({ ...WORK_RECORD, title: undefined })).toThrow(ApiError);
  });
});
