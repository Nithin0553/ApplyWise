/**
 * F10 client-side grouping of approved statements into resume sections.
 *
 * Mirrors the server grouping rule so the preview matches the exported file.
 * The server remains authoritative: this exists to show the user what they
 * will get, never to decide what may be exported.
 */
import type {
  EvidenceSnapshotItem,
  ProvenanceSnapshotItem,
  ResumeVersionSnapshot,
} from "../applications/api";

/**
 * Client-side mirror of the F10 adapter's grouping rule, so the preview on
 * this page is the document the server renders rather than an impression of
 * it. Keep the order and the precedence identical to
 * `app/modules/documents/adapter.py`; if that file changes, change this one.
 */
const SECTIONS: ReadonlyArray<readonly [string, string]> = [
  ["work_experience", "Professional Experience"],
  ["project", "Projects"],
  ["education", "Education"],
  ["certification", "Certifications"],
  ["skill", "Technical Skills"],
];
const FALLBACK_HEADING = "Additional Experience";

function rank(evidenceType: string): number {
  const index = SECTIONS.findIndex(([name]) => name === evidenceType);
  return index === -1 ? SECTIONS.length : index;
}

export interface PreviewEntry {
  organization: string | null;
  role: string | null;
  bullets: string[];
}

export interface PreviewSection {
  heading: string;
  entries: PreviewEntry[];
}

/**
 * The cited record that decides where a statement is filed: the
 * highest-ranking evidence type among those it cites, ties going to the one
 * cited first. Nothing is read from the statement's wording.
 */
function primaryEvidence(
  statement: ProvenanceSnapshotItem,
  byId: Map<string, EvidenceSnapshotItem>,
): EvidenceSnapshotItem | null {
  let best: EvidenceSnapshotItem | null = null;
  for (const id of statement.evidence_ids) {
    const record = byId.get(id);
    if (!record) continue;
    if (best === null || rank(record.evidence_type) < rank(best.evidence_type)) {
      best = record;
    }
  }
  return best;
}

export function buildSections(snapshot: ResumeVersionSnapshot): PreviewSection[] {
  const byId = new Map(snapshot.evidence.map((item) => [item.evidence_id, item]));
  const grouped = new Map<string, Map<string, PreviewEntry>>();

  for (const statement of snapshot.statements) {
    const record = primaryEvidence(statement, byId);
    const heading = record
      ? SECTIONS.find(([name]) => name === record.evidence_type)?.[1] ?? FALLBACK_HEADING
      : FALLBACK_HEADING;
    const organization = record?.organization ?? null;
    const role = record?.role ?? null;
    const key = `${organization ?? ""}\u0000${role ?? ""}`;

    let entries = grouped.get(heading);
    if (!entries) {
      entries = new Map();
      grouped.set(heading, entries);
    }
    const entry = entries.get(key);
    if (entry) entry.bullets.push(statement.text);
    else entries.set(key, { organization, role, bullets: [statement.text] });
  }

  return [...grouped.entries()]
    .sort((a, b) => {
      const index = (heading: string) =>
        SECTIONS.findIndex(([, name]) => name === heading);
      const left = index(a[0]) === -1 ? SECTIONS.length : index(a[0]);
      const right = index(b[0]) === -1 ? SECTIONS.length : index(b[0]);
      return left - right;
    })
    .map(([heading, entries]) => ({ heading, entries: [...entries.values()] }));
}

/**
 * Whether F10 will render this version at all. The server re-checks far more
 * than this at download time; this only spares the user a download that is
 * certain to be refused, and never grants permission on its own.
 */
export function isTrustedVersion(snapshot: ResumeVersionSnapshot): boolean {
  return (
    snapshot.statements.length > 0 &&
    snapshot.statements.every((item) => item.origin === "F09_APPROVED")
  );
}

export function entryLabel(entry: PreviewEntry): string {
  return [entry.role, entry.organization].filter(Boolean).join(", ");
}
