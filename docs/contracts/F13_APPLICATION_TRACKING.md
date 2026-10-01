# F13 Application Tracking and Resume Version Contract

F13 owns job/application tracking and the immutable history of resume versions saved for each application.

## Application lifecycle

Applications are user-owned. The supported statuses are `draft`, `applied`, `interviewing`, `offer`, `accepted`, `rejected`, and `withdrawn`.

The service permits forward progress while allowing users to skip intermediate stages when their history is incomplete. Terminal states (`accepted`, `rejected`, and `withdrawn`) are not reopened through the normal transition method. Corrections that require reopening should be handled as an explicit future product decision rather than silently rewriting history.

When an application moves to `applied`, F13 records the supplied transition date as `applied_on` if that date is not already known. Moving to a terminal state records `closed_on`. Metadata updates validate that `closed_on` cannot precede `applied_on`.

## Ownership boundary

Every application and resume version is scoped to a `user_id`. Domain lookups query by both resource ID and owner. A missing identifier and an identifier owned by another user both raise the same not-found error. This prevents an API layer from revealing whether another user's private application or resume version exists.

Ownership is also enforced in persistence: `resume_versions(application_id, user_id)` has a composite foreign key to `applications(id, user_id)`. A resume version therefore cannot be persisted under a user different from the owner of its application, even if code bypasses the F13 service.

F01 will later supply the authenticated user ID. F13 does not invent a temporary authentication mechanism.

## Resume versions

A resume version belongs to exactly one application. Version numbers start at 1 and increase independently within each application. F13 locks the owned application row before assigning the next number so the persistence contract is safe for concurrent saves on databases that support row locking. A database uniqueness constraint also protects `(application_id, version_number)`.

Saved versions are append-only through the F13 service. There is no update method for a historical resume version. Each version stores a complete serialized `ResumeVersionSnapshot`; creating a later version does not alter earlier snapshots.

The snapshot preserves:

- the user, application, resume-version identifier, and creation time;
- the exact approved evidence content used at save time;
- generated statement text;
- provenance links from statements to evidence IDs;
- verification state (`VERIFIED`, `INFERRED`, or `UNSUPPORTED`); and
- approval state (`UNREVIEWED`, `APPROVED`, or `REJECTED`).

Snapshot validation rejects duplicate evidence IDs, duplicate statement IDs, and provenance references to evidence that is not present in the same snapshot.

## Integration boundaries

F02 remains the source of approved career evidence. F07/F08/F09 supply statement/provenance/verification/approval information. F10 may save or export a resume and associate the resulting artifact with the F13 version, but it must not rewrite the snapshot. F14 sharing/reviewer access should reference a specific saved resume version rather than exposing the complete Career Evidence Profile.
