// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";

import { createEvidence, listEvidence } from "./api";
import type { EvidenceFormValues } from "./types";

afterEach(() => {
  vi.unstubAllGlobals();
});

const API_RECORD = {
  id: "11111111-1111-1111-1111-111111111111",
  user_id: "22222222-2222-2222-2222-222222222222",
  evidence_type: "skill",
  title: "Python",
  organization: null,
  role: null,
  location: null,
  description: "Backend development",
  skill_name: "Python",
  proficiency: "Advanced",
  credential: null,
  url: null,
  start_date: null,
  end_date: null,
  source: "Manual entry",
  status: "unconfirmed",
  approved_at: null,
  created_at: "2026-10-05T12:00:00Z",
  updated_at: "2026-10-05T12:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("evidence api", () => {
  it("lists evidence with the F01 bearer token and maps the backend shape", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([API_RECORD]));
    vi.stubGlobal("fetch", fetchMock);

    const result = await listEvidence("opaque-token");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/evidence/");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer opaque-token");
    expect(result[0]).toMatchObject({
      id: API_RECORD.id,
      evidenceType: "skill",
      title: "Python",
      skillName: "Python",
      status: "unconfirmed",
    });
  });

  it("creates evidence using the backend field names and nulls for empty optional values", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(API_RECORD, 201));
    vi.stubGlobal("fetch", fetchMock);

    const values: EvidenceFormValues = {
      evidenceType: "skill",
      title: " Python ",
      organization: "",
      role: "",
      location: "",
      description: " Backend development ",
      skillName: " Python ",
      proficiency: " Advanced ",
      credential: "",
      url: "",
      startDate: "",
      endDate: "",
      source: " Manual entry ",
    };

    await createEvidence("opaque-token", values);

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      evidence_type: "skill",
      title: "Python",
      organization: null,
      role: null,
      location: null,
      description: "Backend development",
      skill_name: "Python",
      proficiency: "Advanced",
      credential: null,
      url: null,
      start_date: null,
      end_date: null,
      source: "Manual entry",
    });
  });
});
