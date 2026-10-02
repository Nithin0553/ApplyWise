# Foundation Status

**Release:** 0.1.0  
**Last updated:** 2026-10-02

## Completed foundation
- Monorepo structure.
- Separate web and API workspaces.
- PostgreSQL local environment.
- Environment-variable templates.
- Backend configuration and health endpoint.
- Feature-oriented module boundaries.
- AI-provider abstraction.
- CI lint/test/build workflow.
- Dependency/security baseline workflow.
- PR template, issue templates, CODEOWNERS starter.
- Architecture, team workflow, feature boundary, traceability, versioning, and ADR documents.
- Source project artifacts preserved in `docs/source/`.
- Initial six-person workstreams and team GitHub identities documented.
- **F01 User Registration and Authentication / RBAC foundation** merged to `main` in PR #13.

## Implemented feature work pending merge
PR #8 contains completed F02/F13 work plus the F14 sharing foundation:

- **F02 Career Evidence Profile:** structured evidence persistence, approval lifecycle,
  ownership/privacy enforcement, approved-evidence integration contracts, migration, and tests.
- **F13 Resume Version Management and Application Tracking:** user-owned applications,
  lifecycle tracking, immutable application-linked resume versions, snapshot integrity,
  migrations, UI, and tests.
- **F14 Peer Review and Sharing foundation:** secure version-specific share grants, one-way share
  secret storage, revocation/expiry, append-only peer feedback, ownership/version constraints,
  isolated sharing/review UI, tests, and documented F01/F10 seams.

PR #8 is being integrated on top of the merged F01 foundation before it lands in `main`.

## Active integration work
- Wire F02/F13/F14 HTTP boundaries to F01 authenticated identity and role enforcement.
- Keep one Alembic migration chain rooted at F01 revision `0001`.
- F04 job-description analysis prototype is in PR #15.
- F07 grounded generation/provenance is in PR #11.
- F10 resume preview prototype is in PR #14; final document/export work remains follow-up scope.
- F05/F06/F08/F09 still need to complete the job-analysis-to-approved-resume release chain.

## GitHub administration still required
- Ensure all five teammates have the collaborator access needed for their assigned branches/PRs.
- Protect `main` with pull-request, review, CI, and force-push/deletion restrictions.
- Confirm whether the repository should remain public.
- Ensure formal PDF artifacts are preserved in the repository.
