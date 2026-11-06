# Changelog

## [Unreleased]

### Added
- F15 Interview Defensibility Check (`generation` module, `interview` frontend):
  - Backend: `interview_schemas.py`, a deterministic `interview_service.py` and
    `POST /api/interview/preparation`. For each approved statement it returns
    the questions an interviewer is likely to ask, supporting points drawn from
    the user's own cited evidence, and a defensibility risk with the signals
    behind it.
  - The check uses no AI provider. Every signal is a textual comparison between
    an approved statement and the evidence it cites, so the advice is
    deterministic, explainable line by line, and available without F08 or F09.
  - Defensibility is not verification: `InterviewPrep` carries
    `advisory_only: Literal[True]`, and no model in the feature has an
    approval, verification or export field.
  - Cited evidence is resolved server-side through F02, so a caller cannot
    supply material that appears to justify any claim. Missing, foreign-owned
    and unapproved ids all return an identical 404.
  - Statements are still caller-supplied pending F09, so the route reuses F11's
    `require_prototype_environment` guard and returns 404 when
    `APP_ENV=production`.
  - Frontend: `features/interview` — `InterviewPrepPage` ordering the hardest
    statements first, with plain-language labels for every signal.
  - Docs: `docs/contracts/F15_INTERVIEW_DEFENSIBILITY_CONTRACT.md`.

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

### Fixed
- `apps/api/alembic.ini` was missing the `[loggers]`/`[handlers]`/`[formatters]`
  sections that `migrations/env.py`'s `fileConfig()` call needs; the
  migration could not run at all until these were added.
- `apps/api/app/main.py` had no `CORSMiddleware`, so the browser's
  preflight `OPTIONS /auth/register` request 405'd and registration
  silently failed from the Vite dev server — undetected by `pytest`'s
  `TestClient` and the frontend's mocked tests, which don't exercise real
  browser CORS enforcement. Added `CORSMiddleware` wired to a new
  `settings.cors_origins`.
- Added the `REVIEWER` role to `UserRole` (`apps/api/app/modules/auth/models.py`)
  so the role model covers all three product user types from
  `docs/TEAM_ALLOCATION.md`; not wired to any endpoint — see the
  docstring on `UserRole.REVIEWER` for why.
- Changed user identity from `str`/`String(36)` to a native
  `uuid.UUID`/`Uuid(as_uuid=True)` end to end (model, migration, JWT
  subject-claim handling, service layer, response schema) to match the
  identity type other feature modules use.
- Left a coordination note in
  `apps/api/migrations/versions/0001_create_users_table.py`: this
  migration and PR #8's first migration are both currently Alembic roots;
  one needs to set `down_revision="0001"` after the other merges.

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
