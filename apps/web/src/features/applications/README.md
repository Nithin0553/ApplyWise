# F13 Applications UI

Feature-owned UI for resume versions and application tracking.

`ApplicationsPage` is the authenticated F13 integration container. It reads the F01 bearer token through `useAuth()`, loads only the current user's `/api/applications` data, loads each application's saved resume-version history, and maps the backend snake-case DTOs into the existing presentation contracts.

`ApplicationTracker` renders application status, metadata, and saved resume-version history. It emits selection, create, edit, status-transition, and version-open callbacks. Status options mirror the F13 backend lifecycle and expose only valid forward transitions; terminal statuses remain read-only.

`ApplicationForm` covers the F13-owned create/edit metadata flow for company, role, location, job link, source, notes, application date, and next-action date. Text input is normalized before it reaches the API client.

`api.ts` is the F13 frontend boundary for the owner-scoped backend routes. It attaches the F01 bearer token, translates camel-case form values to the backend contract, exposes create/update/status/list/version reads, and preserves immutable resume-version snapshot data for inspection. It also exports `saveResumeVersion(...)` plus `ResumeVersionContent`, which is the safe handoff for later F07/F08/F09/F10 orchestration: callers must supply the evidence/provenance/verification/approval snapshot, while F13/backend creates owner, application, version number, version ID, and timestamps. F13 never invents or promotes statement state.

There is intentionally no generic "Save current resume" button yet. Until the generation/verification/approval pipeline provides a finalized snapshot, showing such a button would require F13 to fabricate content or cross another module's responsibility. The public save API seam is ready for the shared orchestration layer once that upstream content exists.

The feature intentionally does not modify the shared `App.tsx` shell. `ApplicationsPage` is exported from this folder so the shared navigation can mount it once the active shell work is consolidated.
