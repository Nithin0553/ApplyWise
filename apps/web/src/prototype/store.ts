import { createContext, useContext } from "react";

import type { ApprovedStatement } from "../features/cover-letter/api";
import { REVIEW_STATEMENTS } from "./mock";

/**
 * The one piece of state two prototype screens share: which statements the
 * user approved on the Review screen (F09), which is what the Cover letter
 * screen (F11) is allowed to draft from.
 *
 * In the real app this lives in the backend. Here it is deliberately small,
 * so the prototype shows the dependency instead of pretending each screen
 * stands alone.
 */
export interface ApprovalStore {
  approvedIds: string[];
  toggle: (id: string) => void;
}

export const ApprovalContext = createContext<ApprovalStore>({
  approvedIds: [],
  toggle: () => undefined,
});

export function useApprovals(): ApprovalStore {
  return useContext(ApprovalContext);
}

/** Only VERIFIED or INFERRED statements can be approved; UNSUPPORTED never. */
export function approvableIds(): string[] {
  return REVIEW_STATEMENTS.filter((item) => item.state !== "UNSUPPORTED").map((item) => item.id);
}

/** Map the approved review statements into the shape F11's API expects.
 *
 * The narrowing is deliberate: an UNSUPPORTED statement has no representation
 * in `ApprovedStatement`, so it cannot reach the cover letter API at all.
 */
export function toApprovedStatements(approvedIds: string[]): ApprovedStatement[] {
  const statements: ApprovedStatement[] = [];
  for (const item of REVIEW_STATEMENTS) {
    if (!approvedIds.includes(item.id)) continue;
    if (item.state === "UNSUPPORTED") continue;
    statements.push({
      statement_id: item.statement_id,
      text: item.text,
      evidence_ids: item.evidence_ids,
      verification_status: item.state,
      approval_status: "APPROVED",
    });
  }
  return statements;
}
