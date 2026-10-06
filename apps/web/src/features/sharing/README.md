# F14 Sharing UI

Feature-owned UI for controlled peer-review sharing and feedback.

`SharingPage` is the authenticated Job Seeker container. It discovers immutable resume versions
through F13's public HTTP API, loads the current user's F14 grants, creates expiring or non-expiring
links, revokes active grants, and displays owner-visible feedback. The share secret returned by the
backend is kept only long enough to display/copy the newly created link; it is never persisted by the
frontend.

`ReviewerSharePage` is the authenticated Reviewer surface. It resolves a supplied share secret and
submits feedback through the reviewer-only F14 endpoints. The backend remains the authority for
revoked/expired/missing links, which are all exposed outwardly as unavailable shares.

`ShareManager` and `PeerFeedbackPanel` remain presentation components. `PeerFeedbackPanel` can be
read-only for the owner or interactive for a reviewer.

## Integration boundaries

- F01 supplies the bearer token and enforces Job Seeker / Reviewer authorization on the backend.
- F13 remains the source of immutable resume-version identity; F14 discovers versions only through
  F13's API and never reads another module's tables.
- F10 remains responsible for rendering the actual shared resume. The reviewer page therefore shows
  the authorized version reference and feedback surface rather than reconstructing Career Evidence
  Profile data.
- Shared-shell routing still needs to map a `?share=<secret>` URL to `ReviewerSharePage`. This feature
  branch intentionally does not modify `App.tsx` while the shared shell is moving.

Public self-registration currently creates Job Seeker accounts only. Reviewer accounts must be
provisioned through the project-supported role-management path before the reviewer surface can be
exercised end to end.
