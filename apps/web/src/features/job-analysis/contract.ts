// Consumer DTOs mirror docs/F04/analysis-result.schema.json (schema version 1.0).
export type Category = "skill" | "education" | "experience" | "responsibility" | "qualification";
export type Importance = "Critical" | "Preferred" | "Optional";
export interface Requirement {
  id: string;
  text: string;
  categories: Category[];
  importance: Importance | null;
  importance_basis: "explicit" | "section" | "unspecified" | "conflicting";
  source: { text: string; start: number; end: number; line: number; section: string | null };
  experience: {
    minimum_years: number | null; maximum_years: number | null;
    stated_years: number | null; expression: string;
  } | null;
  needs_review: boolean;
  review_reasons: string[];
}
export interface AnalysisResult {
  schema_version: "1.0";
  document_id: string;
  requirements: Requirement[];
  warnings: string[];
}
