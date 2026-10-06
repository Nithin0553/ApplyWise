# F14 Sharing UI

Feature-owned UI for controlled peer-review sharing and feedback.

`SharingPage` is the authenticated Job Seeker container. It discovers immutable resume versions
through F13's public HTTP API, loads the current user's F14 grants, creates expiring or non-expiring
links, revokes active grants, and displays owner-visible feedback. The share secret returned by the
backend is kept only long enough to display/copy the newly created link; it is never persisted by the
frontend. The generated reviewer link stores that one-time secret in the URL fragment (`#share=...`)
rather than the query string, so the browser does not send it as part of the initial page request or
Referer header.

`ReviewerSharePage` is the authenticated Reviewer surface. It reads the share secret from the
client-side URL fragment (or an explicitly supplied integration prop), resolves the share through the
reviewer-only F14 API, and submits reviewer feedback. Reviewer API calls send the raw secret only in
JSON request bodies, never in URL paths or query strings. The backend remains the authority for
revoked/expired/missing links, which are all exposed outwardly as unavailable shares.

`ShareManager` and `PeerFeedbackPanel` remain presentation components. `PeerFeedbackPanel` can be
read-only for the owner or interactive for a reviewer. Owner-facing feedback intentionally labels the
author only as `Reviewer`; F14 does not expose reviewer identity through this UI.

## Integration boundaries

- F01 supplies the bearer token and enforces Job Seeker / Reviewer authorization on the backend.
- F13 remains the source of immutable resume-version identity; F14 discovers versions only through
  F13's API and never reads another module's tables.
- F10 remains responsible for rendering the actual shared resume. The reviewer page therefore shows
  the authorized version reference and feedback surface rather than reconstructing Career Evidence
  Profile data.
- Shared-shell routing still needs to map a `#share=<secret>` URL to `ReviewerSharePage`. This feature
  branch intentionally does not modify `App.tsx` while the shared shell is moving.
- Frontend API calls default to same-origin `/api/...` paths. `VITE_API_BASE_URL` remains an explicit
  override for deployments that intentionally host the API on another origin.
- PR #24 supplies the matching backend reviewer endpoints (`/api/shares/reviewer/resolve` and
  `/api/shares/reviewer/feedback`) and must land before this frontend PR.

Public self-registration currently creates Job Seeker accounts only. Reviewer accounts must be
provisioned through the project-supported role-management path before the reviewer surface can be
exercised end to end.
