# F13 Applications UI

Feature-owned UI for resume versions and application tracking.

`ApplicationsPage` is the authenticated F13 integration container. It reads the F01 bearer token through `useAuth()`, loads only the current user's `/api/applications` data, loads each application's saved resume-version history, and maps the backend snake-case DTOs into the existing presentation contracts.

`ApplicationTracker` renders application status, metadata, and saved resume-version history. It emits selection, create, edit, status-transition, and version-open callbacks. Status options mirror the F13 backend lifecycle and expose only valid forward transitions; terminal statuses remain read-only.

`ApplicationForm` covers the F13-owned create/edit metadata flow for company, role, location, job link, source, notes, application date, and next-action date. Text input is normalized before it reaches the API client.

`api.ts` is the F13 frontend boundary for owner-scoped application and saved-version reads. It attaches the F01 bearer token, translates camel-case form values to the backend contract, exposes application create/update/status/list operations plus version history/detail reads, and preserves immutable resume-version snapshot data for inspection. API calls default to same-origin `/api/...` paths; `VITE_API_BASE_URL` is an explicit deployment override only.

A saved F13 version is a **historical snapshot**, not an export authorization. Per the F13 contract it retains the verification and approval state that existed when the version was saved, including non-final states. F10 owns the separate rule that only content already eligible for finalization may be rendered/exported.

This frontend deliberately does **not** expose a generic `saveResumeVersion(...)` handoff yet. The current backend save contract accepts a snapshot supplied by the caller; wiring that directly to F07/F08/F09/F10 would let browser-supplied snapshot labels become an integration dependency before a trusted server-side materialization/finalization boundary exists. That orchestration should be added only after the server can build the snapshot from authoritative F02/F08/F09 sources.

The feature intentionally does not modify the shared `App.tsx` shell. `ApplicationsPage` is exported from this folder so the shared navigation can mount it once the active shell work is consolidated.
