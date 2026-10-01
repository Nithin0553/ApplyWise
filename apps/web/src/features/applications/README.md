# F13 Applications UI

Feature-owned UI for resume versions and application tracking.

`ApplicationTracker` is deliberately prop-driven. It renders application status, metadata, and saved resume-version history, and emits callbacks for selection/status/version actions. It does not call backend endpoints or derive a user identity itself.

`ApplicationForm` covers the F13-owned create/edit metadata flow for company, role, location, job link, source, notes, application date, and next-action date. It normalizes trimmed text and returns the form values to a parent container rather than owning persistence.

That separation keeps F13 ready for F01 integration: once authentication supplies the current user and the API layer is available, a thin container can load owner-scoped data, map API payloads, and pass them into these components without changing the feature presentation contract.

The status options mirror the F13 backend lifecycle and only expose forward transitions. Terminal statuses are read-only in the normal tracker flow.
