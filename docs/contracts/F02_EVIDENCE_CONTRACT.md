# F02 Approved Evidence Contract

F02 owns the Career Evidence Profile and is the only module that should read or write the evidence persistence model directly.

Evidence is user-owned through `user_id`. New manual or imported evidence begins in the `UNCONFIRMED` state. Only the owning user boundary may transition a record to `APPROVED`; returning a record to `UNCONFIRMED` clears its approval timestamp.

The persistence model keeps structured fields for experience, education, projects, skills, certifications, responsibilities, accomplishments, and supporting details. Consumers should not treat `description` as the complete evidence record.

## Edit and approval rule

Approval applies to the current content of an evidence record, not permanently to its ID. If any editable field of an `APPROVED` record actually changes, F02 automatically returns that record to `UNCONFIRMED` and clears `approved_at`. A no-op update that does not change stored content leaves the current approval intact.

This rule prevents F05/F07/F08 consumers from treating materially edited evidence as though the user had already approved the new content. Existing statement provenance may still keep the evidence ID, but the evidence will no longer appear through the approved-evidence contract until the user reviews and approves it again.

Downstream modules F05, F07, and F08 integrate through `ApprovedEvidenceProvider.list_approved(user_id=...)`. They must not query `evidence_records` directly. The returned contract contains only records whose owner matches the requested user and whose state is `APPROVED`.

The HTTP authentication boundary is intentionally not implemented in F02. F01 owns authentication and role resolution; once F01 lands, an API/router layer can supply the authenticated user ID to `EvidenceService` without changing the F02 domain contract.
