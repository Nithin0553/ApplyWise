# F14 Peer Review and Sharing Contract

F14 shares one immutable F13 resume version at a time and records peer feedback without
changing that historical version.

## Security and privacy boundary

A share grant is owner-scoped and references exactly one saved F13 resume version. Creating
a grant generates a high-entropy opaque secret. Only its SHA-256 digest is persisted; the raw
secret is returned once to the caller so an API/UI layer can build the share link.

Reviewer lookup accepts the raw secret, hashes it, and resolves only an active grant. The raw
secret must not be carried in an API URL path or query string. Reviewer resolution and feedback
submission use authenticated `POST` requests with the secret in the JSON request body so normal
server/proxy access logs do not capture it as part of the request target. Browser-facing share
links should likewise keep the secret in a client-only URL fragment until the reviewer UI sends
it in the authenticated request body.

Missing, expired, revoked, and otherwise invalid share secrets all produce the same domain-level
not-found result. This prevents the sharing boundary from revealing whether an old or invalid
share ever existed.

The reviewer-facing `SharedResumeAccess` contract contains only the share identifier, immutable
resume-version identifier, creation time, and optional expiration. It deliberately excludes the
F13 snapshot, Career Evidence Profile records, evidence IDs, provenance links, verification
details, owner identifiers, application notes, and other private profile data.

## Peer feedback

Peer feedback is append-only through the F14 service. A feedback row is bound to both its share
and the immutable resume version targeted by that share. F14 does not provide update/delete
operations for feedback and never mutates the saved F13 snapshot when feedback is added.

The service accepts a `reviewer_user_id` as an already-resolved identity. It does not decide
whether that identity has the Reviewer role.

## F01 integration

F01 is responsible for authentication and role authorization at the HTTP/API boundary. The
implemented F14 routes:

1. require a `JOB_SEEKER` for owner-only share creation, listing, revocation, and feedback-history operations;
2. require an authenticated `REVIEWER` before resolving a share for review or submitting feedback;
3. accept reviewer share secrets only in the JSON bodies of `/api/shares/reviewer/resolve` and `/api/shares/reviewer/feedback`; and
4. pass only the resolved user UUIDs into `SharingService`.

F14 does not create temporary users, roles, sessions, headers, or bypass credentials. Missing or
foreign-owned owner resources continue to map to the same not-found response.

## F10 integration seam

F14 does not render a resume and does not inspect document-provider internals. Successful share
resolution returns the immutable `resume_version_id`. Once F10's final rendering/export contract
lands, the API/application orchestration layer should pass that identifier through F10's public
contract to obtain the rendered/shareable representation.

This keeps the access decision in F14, immutable content identity in F13, and document rendering
in F10. F10 must not query F14 tables directly, and F14 must not read F10 persistence internals.

## Lifecycle rules

- Owners may create multiple independent grants for the same or different resume versions.
- Owners may list only their grants.
- Revocation is idempotent for the owner.
- Expiration must be in the future when a grant is created.
- Expired and revoked grants cannot resolve or receive new feedback.
- Existing feedback remains part of the audit history after a grant is revoked or expires.
- A share always remains tied to the resume version that existed when it was created.

## Remaining integration work

F01 authentication/RBAC wiring is complete. The remaining F14 integration is the F10-rendered
resume delivery/share page once F10's final document service is available. The secure share and
feedback boundary remains independent of F10 provider internals.
