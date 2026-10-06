# F02 Career Evidence UI

Feature-owned frontend for the Career Evidence Profile already exposed by the F02 backend.

## Included

- Authenticated evidence API client using the bearer token supplied by F01 `useAuth()`.
- Career evidence list with `UNCONFIRMED` / `APPROVED` state shown to the user.
- Add and edit form for the full F02 evidence contract.
- Explicit approve and mark-unconfirmed actions.
- Warning that a real edit to approved evidence causes the backend to revoke approval.
- Filtering, loading, empty, and API-error states.
- Component and API tests using synthetic data only.

## Integration boundary

`EvidenceProfilePage` is the F02 page component for the shared application shell. This branch intentionally does not replace or rewrite `App.tsx` while other feature branches are also integrating the shared shell.

Only backend-approved evidence is eligible to cross the F02 grounding boundary used by F05/F07/F08. The UI never treats an unconfirmed record as approved locally.
