# F13 Applications UI

Feature-owned UI for resume versions and application tracking.

`ApplicationTracker` is deliberately prop-driven. It renders application status, metadata, and saved resume-version history, and emits callbacks for selection/status/version actions. It does not call backend endpoints or derive a user identity itself.

That separation keeps F13 ready for F01 integration: once authentication supplies the current user and the API layer is available, a thin container can load owner-scoped data and pass it into this component without changing the feature presentation contract.

The status options mirror the F13 backend lifecycle and only expose forward transitions. Terminal statuses are read-only in the normal tracker flow.
