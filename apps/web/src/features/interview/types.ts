/**
 * F15 interview defensibility types.
 *
 * These mirror app/modules/generation/interview_schemas.py exactly. Note what
 * is absent: there is no approval, verification or export field anywhere in
 * this file. F15 returns advice, and the UI must never be able to render it as
 * an F08 verification or an F09 approval.
 */

export type DefensibilityRisk = "SUPPORTED" | "NEEDS_DETAIL" | "HARD_TO_DEFEND";

export type SignalCode =
  | "UNSOURCED_NUMBER"
  | "UNSOURCED_SUPERLATIVE"
  | "UNSOURCED_LEADERSHIP"
  | "THIN_EVIDENCE"
  | "INFERRED_STATEMENT"
  | "SINGLE_SOURCE";

export type QuestionKind =
  | "EVIDENCE_PROBE"
  | "SPECIFICS"
  | "OWNERSHIP"
  | "METRIC_SOURCE";

export interface RiskSignal {
  code: SignalCode;
  detail: string;
}

export interface InterviewQuestion {
  question_id: string;
  statement_id: string;
  kind: QuestionKind;
  text: string;
}

export interface StatementPreparation {
  statement_id: string;
  statement_text: string;
  evidence_ids: string[];
  risk: DefensibilityRisk;
  signals: RiskSignal[];
  questions: InterviewQuestion[];
  supporting_points: string[];
}

export interface InterviewPrep {
  prep_id: string;
  user_id: string;
  generated_at: string;
  items: StatementPreparation[];
  advisory_only: true;
}

/** Statements as F09 will supply them. Shaped like the backend model. */
export interface ApprovedStatement {
  statement_id: string;
  text: string;
  evidence_ids: string[];
  verification_status: "VERIFIED" | "INFERRED";
}

/** What the user is told each risk level means, in plain words. */
export const RISK_LABEL: Record<DefensibilityRisk, string> = {
  SUPPORTED: "Your evidence answers this",
  NEEDS_DETAIL: "Be ready with more detail",
  HARD_TO_DEFEND: "Hard to defend as written",
};

/** Why a statement was flagged, phrased for the person rehearsing. */
export const SIGNAL_LABEL: Record<SignalCode, string> = {
  UNSOURCED_NUMBER: "Figure is not in your evidence",
  UNSOURCED_SUPERLATIVE: "Claims a ranking your evidence does not record",
  UNSOURCED_LEADERSHIP: "Claims scope your evidence does not record",
  THIN_EVIDENCE: "Your evidence is brief",
  INFERRED_STATEMENT: "Inferred rather than directly verified",
  SINGLE_SOURCE: "Rests on a single evidence item",
};
