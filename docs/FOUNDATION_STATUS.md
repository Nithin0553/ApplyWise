# Foundation Status

**Release:** 0.1.0  
**Last updated:** 2026-10-01

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
- Source project artifacts preserved in `docs/source/` locally and prepared for repository preservation.
- Initial six-person workstreams and team GitHub identities documented.

## Implemented feature work pending merge
PR #8 contains the repository's first completed feature implementations and remains open against
`main`:

- **F02 Career Evidence Profile:** structured evidence persistence, approval lifecycle,
  ownership/privacy enforcement, approved-evidence integration contracts, migration, UI, and tests.
- **F13 Resume Version Management and Application Tracking:** user-owned applications,
  lifecycle tracking, immutable application-linked resume versions, snapshot integrity,
  migrations, UI, and tests.
- **F14 Peer Review and Sharing foundation:** secure version-specific share grants, one-way share
  secret storage, revocation/expiry, append-only peer feedback, ownership/version constraints,
  isolated sharing/review UI, tests, and documented F01/F10 seams.

No product feature above is part of `main` until PR #8 is reviewed and merged.

## Active or deferred integration work
- F01 must provide authenticated identity and RBAC for Job Seeker/Reviewer/Administrator flows.
- F07 has an active owner branch for grounded generation/provenance.
- F04-F09 still need to complete the job-analysis, selection, generation, verification, and user
  approval chain required by the first release boundary.
- F10 must provide approved resume rendering/export and later connect rendered output to F13/F14
  through public contracts.
- PDF/DOCX processing libraries, final rendering implementation, final design system, production
  hosting, and production secrets remain feature/deployment decisions.

## GitHub administration still required
- Ensure all five teammates have the collaborator access needed for their assigned branches/PRs.
- Protect `main` with pull-request, review, CI, and force-push/deletion restrictions.
- Confirm whether the repository should remain public.
- Ensure formal PDF artifacts are preserved in the repository.
