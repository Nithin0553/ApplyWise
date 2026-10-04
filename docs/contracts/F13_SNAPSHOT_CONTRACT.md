# Early F13 Resume Version Snapshot Contract

A saved resume version must preserve the exact evidence, statement text, provenance links, verification state, and user-approval state used at save time. Later edits to the Career Evidence Profile must not rewrite the historical meaning of an existing resume version.

`ResumeVersionSnapshot` is therefore an immutable contract. It records the owning user, application, resume-version identifier, creation time, approved evidence snapshots, and generated statement snapshots.

Evidence snapshots capture the evidence identifier plus the relevant display/content fields and the approval timestamp. Statement snapshots capture the text, evidence identifiers that support it, verification state (`VERIFIED`, `INFERRED`, or `UNSUPPORTED`), and approval state.

This contract defines the early F13 integration boundary only. Full application tracking, resume-version persistence, sharing, and reviewer behavior remain later F13/F14 work.
