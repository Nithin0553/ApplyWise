# F13 — Trusted resume finalization and F10 export-content boundary

**Coding owner:** @Nithin0553  
**Issue:** #22  
**Dependencies:** F02 approved evidence; F08 current independent verification (owned by @niraalibandi); F09 current user approval (#63).  
**F10 integration owner:** @dhernandez23.

## Purpose

A saved F13 resume version is historical data, **not** proof that the
statements it contains are verified and approved today. The legacy
`POST /api/applications/{id}/resume-versions` is still a historical-draft
endpoint; it rejects browser-asserted `origin: F09_APPROVED`. This feature
adds a distinct server-authoritative materialization path and a current-state
gate which F10 must call before any document export.

## New API

All endpoints require the authenticated F01 **Job Seeker**, and all lookups
are scoped to their user ID:

1. `POST /api/applications/{application_id}/trusted-finalize` with **only**
   `{"statement_ids": ["UUID", ...]}` (1–10 unique IDs). Extra fields,
   including statement text, evidence bodies, verification status and approval
   flags, return 422. The server resolves each selected statement from F09,
   which consults the currently authoritative F08 provider. A selected
   statement must be currently VERIFIED or INFERRED **and** explicitly APPROVED
   for the current revision. UNSUPPORTED, rejected, stale, missing or foreign
   statement IDs are ineligible. The server then loads only current owned
   approved F02 evidence, including approval timestamps. It builds
   `ResumeVersionContent` with `F09_APPROVED` origin and the exact F09
   verification revision on every trusted statement. It persists an immutable
   F13 version under the user's existing application.

2. `GET /api/applications/resume-versions/{resume_version_id}/trusted-export-content`
   is the **F10 handoff**. It does not trust a saved version merely because its
   snapshot says APPROVED or F09_APPROVED. It requires every historical
   statement to have `F09_APPROVED` origin, resolves those statement IDs again
   through current F08/F09, resolves current F02 approved evidence, and compares
   both server-built contents with the historical snapshot exactly, including
   each F09 verification revision. Re-approving identical text on a newer
   revision **does not** retroactively authorize older saved versions. Missing,
   revoked, edited, reclassified or re-approved evidence/statement data fails
   closed. F10 must use this checked content (or the same service method
   `TrustedFinalizationService.current_export_content`) immediately before
   rendering; do **not** use ordinary F13 saved-version retrieval as export
   permission.

## Status distinctions and security

- F08 independently classifies `VERIFIED`, `INFERRED` or `UNSUPPORTED`.
- F09 records human `APPROVED`/`REJECTED` on a specific F08 revision.
- `INFERRED` may pass only with explicit current user approval, and **stays
  INFERRED** in F13; it is never silently upgraded to VERIFIED.
- `UNSUPPORTED` is ineligible for trusted finalization and export.
- Ordinary F13 user-reviewed historical drafts use `DRAFT_USER_REVIEWED`
  origin and are not made eligible by this route.
- Missing or foreign application/version IDs use the same 404 semantics.
  Invalid or no-longer-current selections return 409 without creating a new
  snapshot. F08 unavailability returns 503 without authorizing an operation.
- The router commits a final snapshot only after the authorization checks
  succeed. On failure the transaction rolls back.

**Important integration condition:** This branch is stacked on F09 PR #63.
F08's real `CurrentVerificationProvider` is **not** yet merged; the default
provider continues to return 503. Tests inject a synthetic F08 provider to
exercise the successful trusted path. This implementation must not be called a
live F08/F09 integration, and F10's PDF/DOCX export is not yet implemented.
After F08 is integrated, repeat adversarial and concurrent-change testing,
including source evidence editing, deletion and re-approval.

## Verification plan

Tests in `apps/api/tests/test_f13_trusted_finalization.py` cover:
current approved evidence/statement snapshot materialization, user approval of
INFERRED without status promotion, F08 unavailable failure, stale revisions,
unconfirmed evidence invalidation, unsupported claims, rejected/unknown
selection, owner isolation, client-side status forgery, duplicate IDs,
historical draft denial, exact-revision invalidation even after re-approval
of identical text, and exported-content revalidation.
CI and Security Baseline must pass on the final stacked branch before review.
