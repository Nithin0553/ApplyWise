# F09 — Persistent Statement Review and Approval

**Owner:** @Nithin0553. **Verification dependency:** F08, @niraalibandi, issue #6. **Follow-on:** #22 trusted F13 finalization.

## Overview
F09 persists the job seeker's decision to approve or reject a specific server-verified statement revision. This is distinct from F08's independent claim verification. HTTP clients submit only a statement ID, desired decision and expected revision; they NEVER submit authoritative evidence/text/status or their own VERIFIED label.

F08 must implement the CurrentVerificationProvider interface (apps/api/app/modules/statement_review/contract.py), returning an authenticated owner's canonical statement ID, text, evidence IDs, classification VERIFIED/INFERRED/UNSUPPORTED, and opaque revision. The provider must recheck current F02 approval and ownership. Material edits to source evidence, statement text or verification outcome require rotation/invalidation of the revision, and should never leave an unchanged valid verified record.

## Authenticated HTTP API
- GET /api/statement-review/{statement_id}: review state with authoritative F08 status and finalization eligibility.
- POST /api/statement-review/{statement_id}/decision: JSON containing decision (APPROVED or REJECTED) and expected_revision; 409 for stale revision or attempting to approve UNSUPPORTED.
- GET /api/statement-review/{statement_id}/history: ordered append-only sequence of owner decisions and F08 revisions.
- GET /api/statement-review/approved: currently VERIFIED or INFERRED statements with current user-APPROVED decisions only; suitable for future trusted F13 and F11 consumption.

All routes require F01 Job Seeker access. Missing/foreign IDs use identical 404. Unauthenticated 401, wrong role 403, unavailable F08 503 (no successful decisions written). Duplicate same-decision/revision actions are idempotent; first-write races return a safe 409. No endpoint accepts client-provided verification or approval flags.

## Durable storage and migration
- statement_reviews: one current user/statement decision, verification revision, event_count.
- statement_review_events: append-only sequence, decision, revision and timestamp per review.
- Migration: 20261106_0005_create_statement_reviews.py; revision parent 20261006_0004.

A previous APPROVED row never independently authorizes finalization. The service re-resolves the statement through F08's provider on every decision/read/list; if the revision changed it appears STALE and is excluded. Only current VERIFIED or INFERRED + explicit owner APPROVED yields finalization_eligible true. INFERRED remains labeled INFERRED and must never be misrepresented as VERIFIED; it is the job seeker's explicitly accepted inference, not independent verification. UNSUPPORTED claims can be rejected, but cannot be approved or included in final export. Evidence/text changes rotate the revision and revoke eligibility.

## Integration status
The F08 implementation has not yet merged. Until the F08 module merges, the default dependency supplies UnavailableVerificationProvider and all review/approval routes fail closed with 503. The integration branch uses a lazy server-side adapter that will instantiate F08's VerificationService from the request's database session when the real package is present, with F02 EvidenceService as its authoritative evidence provider. A missing F08 module continues to return 503; unrelated broken imports are not silently masked. Tests explicitly replace that provider with fixtures to exercise persisted F09 operations. The adapter and full F08/F09/F13/F10 flow require a fresh integration test after F08 migrations are linear and merged. This PR is an implementation foundation, not a claim that trusted resume finalization or PDF/Word export is active.

Next: Niraali completes F08's provider and revision contract; Nithin connects the adapter, then issue #22 materializes F13 final snapshots from fresh F02 and F09 records; Daniel's F10 export must use only that server-approved boundary.

Never bypass F08 by trusting client-supplied statement bodies or labels. Keep F08 module changes in Niraali's branch and F09 review-domain changes in Nithin's branch.