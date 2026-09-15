# Developer Onboarding

Every team member should complete this checklist before opening a feature PR.

1. Clone `Nithin0553/ApplyWise`.
2. Read `README.md`, `docs/ARCHITECTURE.md`, `docs/TEAM_WORKFLOW.md`, and `docs/TEAM_ALLOCATION.md`.
3. Copy `.env.example` to `.env` and `apps/web/.env.example` to `apps/web/.env`.
4. Start PostgreSQL with `docker compose up -d db`.
5. Install backend dependencies in a Python 3.12 virtual environment using `pip install -e ".[dev]"` from `apps/api`.
6. Install frontend dependencies using `npm install` from `apps/web`.
7. Verify the backend health test and frontend tests/build run successfully.
8. Claim the GitHub issue assigned to your feature lane.
9. Create a short-lived branch from current `main` using the naming pattern in `docs/TEAM_WORKFLOW.md`.
10. Never commit `.env`, API keys, real resumes, real applicant information, access tokens, or production credentials.

Before requesting review, run the relevant tests and update feature/requirement/test traceability in the PR.
