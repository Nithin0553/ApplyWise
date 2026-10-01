# F02 Approved Evidence Contract

F02 owns the Career Evidence Profile and is the only module that should read or write the evidence persistence model directly.

Evidence is user-owned through `user_id`. New manual or imported evidence begins in the `UNCONFIRMED` state. Only the owning user boundary may transition a record to `APPROVED`; returning a record to `UNCONFIRMED` clears its approval timestamp.

The persistence model keeps structured fields for experience, education, projects, skills, certifications, responsibilities, accomplishments, and supporting details. Consumers should not treat `description` as the complete evidence record.

## Edit and approval rule

Approval applies to the current content of an evidence record, not permanently to its ID. If any editable field of an `APPROVED` record actually changes, F02 automatically returns that record to `UNCONFIRMED` and clears `approved_at`. A no-op update that does not change stored content leaves the current approval intact.

This rule prevents F05/F07/F08 consumers from treating materially edited evidence as though the user had already approved the new content. Existing statement provenance may still keep the evidence ID, but the evidence will no longer appear through the approved-evidence contract until the user reviews and approves it again.

## Downstream grounding contract

Downstream modules F05, F07, and F08 must use the F02 service contract rather than querying `evidence_records` directly. `ApprovedEvidenceProvider.list_approved(user_id=...)` returns the complete approved evidence objects. `list_grounding_contexts(user_id=...)` returns a normalized `EvidenceGroundingContext` intended for matching, generation, and verification adapters.

The grounding context deliberately preserves structured factual fields instead of collapsing them into free text. It includes title, organization, role, location, description, dates, `skill_name`, `proficiency`, and `credential`. F07 should therefore pass skill name, proficiency, and credential through when present rather than silently dropping them. `source` and `source_url` are retained as provenance metadata; a URL by itself is not a factual claim and should not be turned into resume content merely because it exists.

Every grounding context comes only from evidence in the `APPROVED` state and retains its evidence ID and approval timestamp for provenance.

## Ownership and enumeration safety

F02 scopes single-record lookups by both `evidence_id` and `user_id`. A missing ID and an ID owned by another user both raise the same `EvidenceNotFoundError`. This is intentional: the future HTTP layer should map both cases to the same not-found response so callers cannot probe whether another user's private evidence ID exists.

The HTTP authentication boundary itself is intentionally not implemented in F02. F01 owns authentication and role resolution; once F01 lands, an API/router layer can supply the authenticated user ID to `EvidenceService` without changing the F02 domain contract.
