# Changelog

## [Unreleased]

### Added
- F01 User Registration and Authentication / RBAC foundation (`auth` module):
  - Backend: `users` table and Alembic migration, bcrypt password hashing,
    JWT access tokens, `/auth/register`, `/auth/login`, `/auth/me`, and the
    `get_current_user` / `require_role` dependencies other modules will use
    to enforce authorization server-side.
  - Frontend: `features/auth` — `AuthProvider`/`useAuth()`, `RequireRole`,
    and registration/login forms, wired into the app shell.
  - Self-registration always creates a `job_seeker` account; administrator
    accounts are provisioned out of band so no request can self-elevate.
  - Tests: `apps/api/tests/test_auth.py` (registration, login, RBAC gating)
    and `apps/web/src/features/auth/*.test.tsx`.

## [0.1.0] - 2026-09-15

### Added
- Initial ApplyWise engineering foundation.
- Monorepo structure for frontend and backend.
- PostgreSQL/Docker Compose local environment.
- FastAPI health endpoint and configuration layer.
- Feature-oriented backend module boundaries for F01-F16.
- AI provider abstraction.
- CI and security-baseline workflows.
- Test scaffolding.
- GitHub PR/issue templates and CODEOWNERS starter.
- Architecture, workflow, traceability, versioning, and foundation documentation.

### Not implemented
No product feature is marked complete in version 0.1.0. This release intentionally stops at shared setup so the six team members can split feature work cleanly.
