# ApplyWise

**Course:** COSC 6370 Advanced Software Engineering  
**Team:** Team Islanders

ApplyWise is a web-based resume customization and job-application assistant. Its central trust rule is that generated content must remain grounded in career evidence reviewed and approved by the user.

This repository begins with the shared engineering foundation: architecture boundaries, local development setup, CI, test scaffolding, team workflow, feature traceability, issue/PR conventions, and version/change records before feature implementation starts.

See `docs/FOUNDATION_STATUS.md`, `docs/ARCHITECTURE.md`, `docs/TEAM_WORKFLOW.md`, `docs/FEATURE_BOUNDARIES.md`, and `CHANGELOG.md`.

## Collaboration rule

Nobody develops directly on `main`. Every change follows:

`Issue -> short-lived branch -> tests -> pull request -> CI -> review -> merge`

Current foundation version: **0.1.0**


## Preview the frontend without an account

ApplyWise provides an **Explore Demo** button below sign-in. It opens the current
prototype pages with clearly marked, synthetic sample content. Demo sessions
are temporary and run only in the browser: they do not create an account,
store a token, call authenticated endpoints, or save changes.

For local UI review, run `cd apps/web && npm ci && npm run dev` and visit
`http://localhost:5173`. On a hosted frontend preview, the demo also works
without a deployed API. Real registration, login, evidence persistence, and
server-generated documents still require the API and database. Some prototype
controls are visual previews and are not yet wired to live actions.
