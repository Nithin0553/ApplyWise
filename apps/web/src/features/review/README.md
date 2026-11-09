# F09 — Statement Review and Approval UI

StatementReviewPage is a reusable authenticated F09 view that fetches canonical
F08 verified statement text and its current revision from the F09 API, then
sends only a user decision and the expected revision. It shows independent
verification separately from the human review status and never claims final
export eligibility merely because a statement was reviewed.

The UI is intentionally **not linked from GuidedJourney** until Niraali's F08
provider lands. Without F08, all F09 endpoints return 503 by design; the
component offers a retry action and cannot create an approval.

Owner: Nithin. Integration: F08 #6, F09 #58, F13 finalization #22.
